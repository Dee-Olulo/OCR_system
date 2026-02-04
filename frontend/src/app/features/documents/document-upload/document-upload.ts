// frontend/src/app/features/documents/document-upload/document-upload.component.ts

import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { DocumentService } from '../../../core/services/document';

@Component({
  selector: 'app-document-upload',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatSnackBarModule
  ],
  templateUrl: './document-upload.html',
  styleUrls: ['./document-upload.scss']
})
export class DocumentUploadComponent {
  private documentService = inject(DocumentService);
  private router = inject(Router);
  private snackBar = inject(MatSnackBar);
  
  selectedFile: File | null = null;
  uploading = false;
  dragOver = false;
  
  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (file) {
      this.validateAndSetFile(file);
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
    
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.validateAndSetFile(files[0]);
    }
  }
  
  validateAndSetFile(file: File): void {
    // Validate file type - Phase 2: Added PDF, DOCX, XLSX, PPTX
    const allowedTypes = [
      'image/jpeg', 'image/jpg', 'image/png', 'image/tiff',
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // DOCX
      'application/msword', // DOC
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // XLSX
      'application/vnd.ms-excel', // XLS
      'application/vnd.openxmlformats-officedocument.presentationml.presentation', // PPTX
      'application/vnd.ms-powerpoint' // PPT
    ];
    
    if (!allowedTypes.includes(file.type)) {
      this.snackBar.open('Invalid file type. Supported: Images, PDF, DOCX, XLSX, PPTX', 'Close', { duration: 5000 });
      return;
    }
    
    // Validate file size (50MB for Phase 2)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      this.snackBar.open('File size exceeds 50MB limit.', 'Close', { duration: 5000 });
      return;
    }
    
    this.selectedFile = file;
  }
  
  removeFile(): void {
    this.selectedFile = null;
  }
  
  uploadFile(): void {
    if (!this.selectedFile) {
      return;
    }
    
    this.uploading = true;
    
    this.documentService.uploadDocument(this.selectedFile).subscribe({
      next: (document) => {
        this.snackBar.open('Document uploaded successfully!', 'Close', { duration: 3000 });
        this.router.navigate(['/documents', document.id]);
      },
      error: (error) => {
        this.uploading = false;
        const message = error.error?.detail || 'Upload failed. Please try again.';
        this.snackBar.open(message, 'Close', { duration: 5000 });
      }
    });
  }
  
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  }
}