// // frontend/src/app/features/documents/document-upload/document-upload.component.ts

// import { Component, inject } from '@angular/core';
// import { CommonModule } from '@angular/common';
// import { Router } from '@angular/router';
// import { MatCardModule } from '@angular/material/card';
// import { MatButtonModule } from '@angular/material/button';
// import { MatIconModule } from '@angular/material/icon';
// import { MatProgressBarModule } from '@angular/material/progress-bar';
// import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
// import { DocumentService } from '../../../core/services/document';

// @Component({
//   selector: 'app-document-upload',
//   standalone: true,
//   imports: [
//     CommonModule,
//     MatCardModule,
//     MatButtonModule,
//     MatIconModule,
//     MatProgressBarModule,
//     MatSnackBarModule
//   ],
//   templateUrl: './document-upload.html',
//   styleUrls: ['./document-upload.scss']
// })
// export class DocumentUploadComponent {
//   private documentService = inject(DocumentService);
//   private router = inject(Router);
//   private snackBar = inject(MatSnackBar);
  
//   selectedFile: File | null = null;
//   uploading = false;
//   dragOver = false;
  
//   // Validate by extension — more reliable than file.type across browsers
//   private allowedExtensions = [
//     '.jpg', '.jpeg', '.png', '.tiff', '.tif',
//     '.pdf',
//     '.docx', '.doc',
//     '.xlsx', '.xls'
//   ];
//   onFileSelected(event: any): void {
//     const file = event.target.files[0];
//     if (file) {
//       this.validateAndSetFile(file);
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
    
//     const files = event.dataTransfer?.files;
//     if (files && files.length > 0) {
//       this.validateAndSetFile(files[0]);
//     }
//   }
  
//   validateAndSetFile(file: File): void {
//     // Validate file type
//     const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/tiff', ];
//     if (!allowedTypes.includes(file.type)) {
//       this.snackBar.open('Invalid file type. Please upload JPG, PNG, or TIFF images.', 'Close', { duration: 5000 });
//       return;
//     }
    
//     // Validate file size (10MB)
//     const maxSize = 50 * 1024 * 1024; // 50MB
//     if (file.size > maxSize) {
//       this.snackBar.open('File size exceeds 10MB limit.', 'Close', { duration: 5000 });
//       return;
//     }
    
//     this.selectedFile = file;
//   }
  
//   removeFile(): void {
//     this.selectedFile = null;
//   }
  
//   uploadFile(): void {
//     if (!this.selectedFile) {
//       return;
//     }
    
//     this.uploading = true;
    
//     this.documentService.uploadDocument(this.selectedFile).subscribe({
//       next: (document) => {
//         this.snackBar.open('Document uploaded successfully!', 'Close', { duration: 3000 });
//         this.router.navigate(['/documents', document.id]);
//       },
//       error: (error) => {
//         this.uploading = false;
//         const message = error.error?.detail || 'Upload failed. Please try again.';
//         this.snackBar.open(message, 'Close', { duration: 5000 });
//       }
//     });
//   }
  
//   formatFileSize(bytes: number): string {
//     if (bytes === 0) return '0 Bytes';
//     const k = 1024;
//     const sizes = ['Bytes', 'KB', 'MB', 'GB'];
//     const i = Math.floor(Math.log(bytes) / Math.log(k));
//     return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
//   }
// }

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

  // Validate by extension — more reliable than file.type across browsers
  private allowedExtensions = [
    '.jpg', '.jpeg', '.png', '.tiff', '.tif',
    '.pdf',
    '.docx', '.doc',
    '.xlsx', '.xls'
  ];

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
    // Get extension from filename
    const fileName = file.name.toLowerCase();
    const ext = '.' + fileName.split('.').pop();

    if (!this.allowedExtensions.includes(ext)) {
      this.snackBar.open(
        `Invalid file type "${ext}". Supported: JPG, PNG, TIFF, PDF, DOCX, XLSX`,
        'Close',
        { duration: 5000 }
      );
      return;
    }

    // Validate file size (50MB)
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
    if (!this.selectedFile) return;

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