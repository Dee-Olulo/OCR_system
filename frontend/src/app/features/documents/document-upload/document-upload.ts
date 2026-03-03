// // frontend/src/app/features/documents/document-upload/document-upload.ts

// import { Component, inject } from '@angular/core';
// import { CommonModule } from '@angular/common';
// import { HttpClient } from '@angular/common/http';
// import { Router } from '@angular/router';
// import { MatCardModule } from '@angular/material/card';
// import { MatButtonModule } from '@angular/material/button';
// import { MatIconModule } from '@angular/material/icon';
// import { MatProgressBarModule } from '@angular/material/progress-bar';
// import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
// import { switchMap, catchError, of } from 'rxjs';
// import { DocumentService } from '../../../core/services/document';
// import { Document } from '../../../core/models/document.model';
// import { environment } from '../../../../environments/environment';

// /**
//  * Upload flow (Phase 5):
//  *
//  *   1. User drops / selects a file → validateAndSetFile()
//  *   2. uploadFile() calls POST /api/v1/documents/upload  → FastAPI saves file + MongoDB record
//  *   3. On success, calls POST {n8nWebhookUrl}            → n8n triggers the pipeline
//  *   4. n8n calls POST /api/v1/webhook/process            → OCR + LLM + score + route
//  *   5. Navigates to /documents/:id where the user sees live results
//  *
//  * The n8n call is fire-and-forget from the frontend perspective.
//  * The pipeline runs asynchronously. The document-detail page polls
//  * or the user manually refreshes to see the completed state.
//  */
// @Component({
//   selector: 'app-document-upload',
//   standalone: true,
//   imports: [
//     CommonModule,
//     MatCardModule,
//     MatButtonModule,
//     MatIconModule,
//     MatProgressBarModule,
//     MatSnackBarModule,
//   ],
//   templateUrl: './document-upload.html',
//   styleUrls: ['./document-upload.scss'],
// })
// export class DocumentUploadComponent {
//   private documentService = inject(DocumentService);
//   private http            = inject(HttpClient);
//   private router          = inject(Router);
//   private snackBar        = inject(MatSnackBar);

//   selectedFile: File | null = null;
//   uploading                 = false;
//   triggeringPipeline        = false;
//   dragOver                  = false;

//   private allowedExtensions = [
//     '.jpg', '.jpeg', '.png', '.tiff', '.tif',
//     '.pdf',
//     '.docx', '.doc',
//     '.xlsx', '.xls',
//   ];

//   // ── Drag & drop / file selection ──────────────────────────────────────

//   onFileSelected(event: Event): void {
//     const input = event.target as HTMLInputElement;
//     if (input.files?.[0]) {
//       this.validateAndSetFile(input.files[0]);
//     }
//   }

//   onDragOver(event: DragEvent): void {
//     event.preventDefault();
//     event.stopPropagation();
//     this.dragOver = true;
//   }

//   onDragLeave(event: DragEvent): void {
//     event.preventDefault();
//     event.stopPropagation();
//     this.dragOver = false;
//   }

//   onDrop(event: DragEvent): void {
//     event.preventDefault();
//     event.stopPropagation();
//     this.dragOver = false;
//     const file = event.dataTransfer?.files[0];
//     if (file) {
//       this.validateAndSetFile(file);
//     }
//   }

//   validateAndSetFile(file: File): void {
//     const ext = '.' + file.name.toLowerCase().split('.').pop();

//     if (!this.allowedExtensions.includes(ext)) {
//       this.snackBar.open(
//         `Unsupported file type "${ext}". Allowed: JPG, PNG, TIFF, PDF, DOCX, XLSX`,
//         'Close',
//         { duration: 5000 },
//       );
//       return;
//     }

//     const maxSize = 50 * 1024 * 1024; // 50 MB
//     if (file.size > maxSize) {
//       this.snackBar.open('File exceeds the 50 MB limit.', 'Close', { duration: 5000 });
//       return;
//     }

//     this.selectedFile = file;
//   }

//   removeFile(): void {
//     this.selectedFile = null;
//   }

//   // ── Upload + pipeline trigger ──────────────────────────────────────────

//   uploadFile(): void {
//     if (!this.selectedFile) return;

//     this.uploading = true;

//     this.documentService
//       .uploadDocument(this.selectedFile)
//       .pipe(
//         // Step 1 succeeded — now trigger the n8n pipeline
//         switchMap((doc: Document) => {
//           this.uploading         = false;
//           this.triggeringPipeline = true;

//           this.snackBar.open(
//             '✅ Upload complete — starting processing pipeline...',
//             'Close',
//             { duration: 3000 },
//           );

//           // POST to n8n production webhook.
//           // n8n responds immediately (the pipeline runs asynchronously).
//           // We navigate to the document detail page immediately after.
//           return this.http
//             .post(
//               environment.n8nWebhookUrl,
//               { document_id: doc.id },
//             )
//             .pipe(
//               catchError((err) => {
//                 // n8n not reachable or workflow not activated.
//                 // Log the error but don't block the user — they can
//                 // manually run OCR+LLM from the document detail page.
//                 console.error('n8n webhook call failed:', err);
//                 this.snackBar.open(
//                   '⚠️ Upload saved, but pipeline could not be triggered. ' +
//                   'Check that the n8n workflow is Activated.',
//                   'Close',
//                   { duration: 7000 },
//                 );
//                 return of(null);
//               }),
//               // Carry the document id forward regardless of n8n success
//               switchMap(() => of(doc)),
//             );
//         }),
//       )
//       .subscribe({
//         next: (doc: Document | null) => {
//           this.triggeringPipeline = false;
//           if (doc) {
//             this.router.navigate(['/documents', doc.id]);
//           }
//         },
//         error: (error) => {
//           this.uploading         = false;
//           this.triggeringPipeline = false;
//           const message = error.error?.detail || 'Upload failed. Please try again.';
//           this.snackBar.open(message, 'Close', { duration: 5000 });
//         },
//       });
//   }

//   // ── Display helpers ────────────────────────────────────────────────────

//   get isProcessing(): boolean {
//     return this.uploading || this.triggeringPipeline;
//   }

//   get statusLabel(): string {
//     if (this.uploading)         return 'Uploading...';
//     if (this.triggeringPipeline) return 'Triggering pipeline...';
//     return 'Upload';
//   }

//   formatFileSize(bytes: number): string {
//     if (bytes === 0) return '0 Bytes';
//     const k     = 1024;
//     const sizes = ['Bytes', 'KB', 'MB', 'GB'];
//     const i     = Math.floor(Math.log(bytes) / Math.log(k));
//     return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
//   }
// }

// frontend/src/app/features/documents/document-upload/document-upload.ts

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
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
    if (input.files?.[0]) {
      this.validateAndSetFile(input.files[0]);
    }
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
    if (file) {
      this.validateAndSetFile(file);
    }
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
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
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

          // POST to n8n production webhook with the shared secret header.
          // n8n verifies this header against the Header Auth credential.
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
                // n8n not reachable or workflow not activated.
                // File is already saved — user can run OCR manually.
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
          if (doc) {
            this.router.navigate(['/documents', doc.id]);
          }
        },
        error: (error) => {
          this.uploading          = false;
          this.triggeringPipeline = false;
          const message = error.error?.detail || 'Upload failed. Please try again.';
          this.snackBar.open(message, 'Close', { duration: 5000 });
        },
      });
  }

  // ── Display helpers ────────────────────────────────────────────────────

  get isProcessing(): boolean {
    return this.uploading || this.triggeringPipeline;
  }

  get statusLabel(): string {
    if (this.uploading)          return 'Uploading...';
    if (this.triggeringPipeline) return 'Triggering pipeline...';
    return 'Upload';
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k     = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i     = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  }
}