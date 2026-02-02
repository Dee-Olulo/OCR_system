// frontend/src/app/features/documents/document-list/document-list.component.ts

import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { DocumentService } from '../../../core/services/document';
import { Document } from '../../../core/models/document.model';

@Component({
  selector: 'app-document-list',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatPaginatorModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule
  ],
  templateUrl: './document-list.html',
  styleUrls: ['./document-list.scss']
})
export class DocumentListComponent implements OnInit {
  private documentService = inject(DocumentService);
  private router = inject(Router);
  private snackBar = inject(MatSnackBar);
  
  documents: Document[] = [];
  displayedColumns: string[] = ['filename', 'status', 'uploaded_at', 'file_size', 'actions'];
  loading = true;
  
  // Pagination
  pageSize = 10;
  pageIndex = 0;
  totalDocuments = 0;
  
  ngOnInit(): void {
    this.loadDocuments();
  }
  
  loadDocuments(): void {
    this.loading = true;
    const skip = this.pageIndex * this.pageSize;
    
    this.documentService.getDocuments(skip, this.pageSize).subscribe({
      next: (documents) => {
        this.documents = documents;
        this.totalDocuments = documents.length; // Note: Backend doesn't return total count
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading documents:', error);
        this.snackBar.open('Failed to load documents', 'Close', { duration: 3000 });
        this.loading = false;
      }
    });
  }
  
  onPageChange(event: PageEvent): void {
    this.pageSize = event.pageSize;
    this.pageIndex = event.pageIndex;
    this.loadDocuments();
  }
  
  viewDocument(document: Document): void {
    this.router.navigate(['/documents', document.id]);
  }
  
  downloadDocument(document: Document, event: Event): void {
    event.stopPropagation();
    
    this.documentService.downloadDocument(document.id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = window.document.createElement('a');
        link.href = url;
        link.download = document.filename;
        link.click();
        window.URL.revokeObjectURL(url);
        this.snackBar.open('Download started', 'Close', { duration: 2000 });
      },
      error: (error) => {
        console.error('Download error:', error);
        this.snackBar.open('Download failed', 'Close', { duration: 3000 });
      }
    });
  }
  
  deleteDocument(document: Document, event: Event): void {
    event.stopPropagation();
    
    if (!confirm(`Are you sure you want to delete "${document.filename}"?`)) {
      return;
    }
    
    this.documentService.deleteDocument(document.id).subscribe({
      next: () => {
        this.snackBar.open('Document deleted successfully', 'Close', { duration: 3000 });
        this.loadDocuments();
      },
      error: (error) => {
        console.error('Delete error:', error);
        this.snackBar.open('Failed to delete document', 'Close', { duration: 3000 });
      }
    });
  }
  
  getStatusColor(status: string): string {
    switch (status) {
      case 'completed': return 'primary';
      case 'processing': return 'accent';
      case 'failed': return 'warn';
      default: return '';
    }
  }
  
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  }
  
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  }
}