// frontend/src/app/features/documents/document-list/document-list.component.ts

import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { DocumentService } from '../../../core/services/document';
import { Document } from '../../../core/models/document.model';

@Component({
  selector: 'app-document-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatSnackBarModule,
    MatTooltipModule,
  ],
  templateUrl: './document-list.html',
  styleUrls: ['./document-list.scss'],
})
export class DocumentListComponent implements OnInit {
  private documentService = inject(DocumentService);
  private router          = inject(Router);
  private snackBar        = inject(MatSnackBar);

  documents:         Document[] = [];
  filteredDocuments: Document[] = [];
  loading = true;

  // Table columns
  displayedColumns = ['filename', 'status', 'file_type', 'file_size', 'uploaded_at', 'actions'];

  // Search & filter
  searchQuery  = '';
  activeFilter = 'all';

  // Pagination
  currentPage     = 0;
  pageSize        = 10;
  pageSizeOptions = [5, 10, 25, 50];

  // ── Lifecycle ────────────────────────────────────────────────────────────

  ngOnInit(): void {
    this.loadDocuments();
  }

  loadDocuments(): void {
    this.loading = true;
    this.documentService.getDocuments().subscribe({
      next: (docs) => {
        this.documents         = docs;
        this.filteredDocuments = docs;
        this.loading           = false;
        this.applyFilters();
      },
      error: () => {
        this.snackBar.open('Failed to load documents', 'Close', { duration: 3000 });
        this.loading = false;
      },
    });
  }

  // ── Computed ─────────────────────────────────────────────────────────────

  get totalDocuments(): number {
    return this.documents.length;
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.filteredDocuments.length / this.pageSize));
  }

  get pageStart(): number {
    if (this.filteredDocuments.length === 0) return 0;
    return this.currentPage * this.pageSize + 1;
  }

  get pageEnd(): number {
    return Math.min((this.currentPage + 1) * this.pageSize, this.filteredDocuments.length);
  }

  get pagedDocuments(): Document[] {
    const start = this.currentPage * this.pageSize;
    return this.filteredDocuments.slice(start, start + this.pageSize);
  }

  countByStatus(status: string): number {
    return this.documents.filter(d => d.status === status).length;
  }

  // ── Filtering ────────────────────────────────────────────────────────────

  onSearch(): void {
    this.currentPage = 0;
    this.applyFilters();
  }

  setFilter(filter: string): void {
    this.activeFilter = filter;
    this.currentPage  = 0;
    this.applyFilters();
  }

  private applyFilters(): void {
    let result = [...this.documents];

    // Status filter
    if (this.activeFilter === 'pending') {
      result = result.filter(d => d.status === 'pending' || d.status === 'processing');
    } else if (this.activeFilter !== 'all') {
      result = result.filter(d => d.status === this.activeFilter);
    }

    // Search
    const q = this.searchQuery.trim().toLowerCase();
    if (q) {
      result = result.filter(d => d.filename.toLowerCase().includes(q));
    }

    this.filteredDocuments = result;
  }

  // ── Pagination ────────────────────────────────────────────────────────────

  prevPage(): void {
    if (this.currentPage > 0) this.currentPage--;
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages - 1) this.currentPage++;
  }

  onPageSizeChange(): void {
    this.currentPage = 0;
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  viewDocument(doc: Document): void {
    this.router.navigate(['/documents', doc.id]);
  }

  downloadDocument(doc: Document, event: Event): void {
    event.stopPropagation();
    this.documentService.downloadDocument(doc.id).subscribe({
      next: (blob) => {
        const url  = URL.createObjectURL(blob);
        const link = window.document.createElement('a');
        link.href     = url;
        link.download = doc.filename;
        link.click();
        URL.revokeObjectURL(url);
      },
      error: () => this.snackBar.open('Download failed', 'Close', { duration: 3000 }),
    });
  }

  deleteDocument(doc: Document, event: Event): void {
    event.stopPropagation();
    if (!confirm(`Delete "${doc.filename}"?`)) return;

    this.documentService.deleteDocument(doc.id).subscribe({
      next: () => {
        this.snackBar.open('Document deleted', 'Close', { duration: 3000 });
        this.loadDocuments();
      },
      error: () => this.snackBar.open('Delete failed', 'Close', { duration: 3000 }),
    });
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

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

  getExtension(filename: string): string {
    return filename.split('.').pop()?.toUpperCase() || '—';
  }

  formatFileSize(bytes: number): string {
    if (!bytes) return '0 B';
    const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
      + ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  }

  // Legacy — kept for compatibility if used elsewhere
  getStatusColor(status: string): string {
    const map: Record<string, string> = {
      completed: 'primary',
      pending:   'accent',
      failed:    'warn',
    };
    return map[status] || 'default';
  }

  onPageChange(event: any): void {
    this.currentPage = event.pageIndex;
    this.pageSize    = event.pageSize;
  }
}