// frontend/src/app/features/documents/document-upload/document-upload.ts
// No changes to logic — only adds getFileIcon() helper used by the new template.

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { switchMap, catchError, of } from 'rxjs';
import { DocumentService } from '../../../core/services/document';
import { Document } from '../../../core/models/document.model';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-document-upload',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  templateUrl: './document-upload.html',
  styleUrls: ['./document-upload.scss'],
})
export class DocumentUploadComponent {
  private documentService = inject(DocumentService);
  private http            = inject(HttpClient);
  private router          = inject(Router);
  private snackBar        = inject(MatSnackBar);

  selectedFile: File | null = null;
  uploading                 = false;
  triggeringPipeline        = false;
  dragOver                  = false;

  private allowedExtensions = [
    '.jpg', '.jpeg', '.png', '.tiff', '.tif',
    '.pdf', '.docx', '.doc', '.xlsx', '.xls',
  ];

  // ── Drag & drop / file selection ──────────────────────────────────────

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.[0]) this.validateAndSetFile(input.files[0]);
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver = false;
    const file = event.dataTransfer?.files[0];
    if (file) this.validateAndSetFile(file);
  }

  validateAndSetFile(file: File): void {
    const ext = '.' + file.name.toLowerCase().split('.').pop();
    if (!this.allowedExtensions.includes(ext)) {
      this.snackBar.open(
        `Unsupported file type "${ext}". Allowed: JPG, PNG, TIFF, PDF, DOCX, XLSX`,
        'Close',
        { duration: 5000 },
      );
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      this.snackBar.open('File exceeds the 50 MB limit.', 'Close', { duration: 5000 });
      return;
    }
    this.selectedFile = file;
  }

  removeFile(): void {
    this.selectedFile = null;
  }

  // ── Upload + pipeline trigger ──────────────────────────────────────────

  uploadFile(): void {
    if (!this.selectedFile) return;
    this.uploading = true;

    this.documentService
      .uploadDocument(this.selectedFile)
      .pipe(
        switchMap((doc: Document) => {
          this.uploading          = false;
          this.triggeringPipeline = true;

          this.snackBar.open(
            '✅ Upload complete — starting processing pipeline...',
            'Close',
            { duration: 3000 },
          );

          return this.http
            .post(
              environment.n8nWebhookUrl,
              { document_id: doc.id },
              {
                headers: {
                  'Content-Type':     'application/json',
                  'X-Webhook-Secret': environment.n8nWebhookSecret,
                },
              },
            )
            .pipe(
              catchError((err) => {
                console.error('n8n webhook call failed:', err);
                this.snackBar.open(
                  '⚠️ Upload saved, but pipeline could not be triggered. ' +
                  'Check that the n8n workflow is Activated.',
                  'Close',
                  { duration: 7000 },
                );
                return of(null);
              }),
              switchMap(() => of(doc)),
            );
        }),
      )
      .subscribe({
        next: (doc: Document | null) => {
          this.triggeringPipeline = false;
          if (doc) this.router.navigate(['/documents', doc.id]);
        },
        error: (error) => {
          this.uploading          = false;
          this.triggeringPipeline = false;
          const message = error.error?.detail || 'Upload failed. Please try again.';
          this.snackBar.open(message, 'Close', { duration: 5000 });
        },
      });
  }

  // ── Computed ───────────────────────────────────────────────────────────

  get isProcessing(): boolean {
    return this.uploading || this.triggeringPipeline;
  }

  get statusLabel(): string {
    if (this.uploading)          return 'Uploading...';
    if (this.triggeringPipeline) return 'Triggering pipeline...';
    return 'Upload & Start Pipeline';
  }

  // ── Helpers ────────────────────────────────────────────────────────────

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k     = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i     = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  }

  getFileIcon(filename: string): string {
    const ext = filename.toLowerCase().split('.').pop();
    const map: Record<string, string> = {
      pdf:  'picture_as_pdf',
      docx: 'description',
      doc:  'description',
      xlsx: 'table_chart',
      xls:  'table_chart',
      jpg:  'image',
      jpeg: 'image',
      png:  'image',
      tiff: 'image',
      tif:  'image',
    };
    return map[ext || ''] || 'insert_drive_file';
  }
}