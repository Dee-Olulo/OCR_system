// // frontend/src/app/features/documents/document-detail/document-detail.component.ts

// import { Component, OnInit, inject } from '@angular/core';
// import { CommonModule } from '@angular/common';
// import { ActivatedRoute, Router } from '@angular/router';
// import { MatCardModule } from '@angular/material/card';
// import { MatButtonModule } from '@angular/material/button';
// import { MatIconModule } from '@angular/material/icon';
// import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
// import { MatChipsModule } from '@angular/material/chips';
// import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
// import { MatDividerModule } from '@angular/material/divider';
// import { MatSelectModule } from '@angular/material/select';
// import { FormsModule } from '@angular/forms';
// import { DocumentService } from '../../../core/services/document';
// import { OcrService } from '../../../core/services/ocr';
// import { Document } from '../../../core/models/document.model';

// @Component({
//   selector: 'app-document-detail',
//   standalone: true,
//   imports: [
//     CommonModule,
//     FormsModule,
//     MatCardModule,
//     MatButtonModule,
//     MatIconModule,
//     MatProgressSpinnerModule,
//     MatChipsModule,
//     MatSnackBarModule,
//     MatDividerModule,
//     MatSelectModule
//   ],
//   templateUrl: './document-detail.html',
//   styleUrls: ['./document-detail.scss']
// })
// export class DocumentDetailComponent implements OnInit {
//   private route = inject(ActivatedRoute);
//   private router = inject(Router);
//   private documentService = inject(DocumentService);
//   private ocrService = inject(OcrService);
//   private snackBar = inject(MatSnackBar);
  
//   document: Document | null = null;
//   loading = true;
//   processing = false;
//   selectedEngine: 'tesseract' | 'easyocr' | 'both' = 'tesseract';
  
//   ngOnInit(): void {
//     const documentId = this.route.snapshot.paramMap.get('id');
//     if (documentId) {
//       this.loadDocument(documentId);
//     }
//   }
  
//   loadDocument(id: string): void {
//     this.loading = true;
    
//     this.documentService.getDocument(id).subscribe({
//       next: (document) => {
//         this.document = document;
//         this.loading = false;
//       },
//       error: (error) => {
//         console.error('Error loading document:', error);
//         this.snackBar.open('Failed to load document', 'Close', { duration: 3000 });
//         this.loading = false;
//         this.router.navigate(['/documents']);
//       }
//     });
//   }
  
//   processWithOCR(): void {
//     if (!this.document) return;
    
//     this.processing = true;
    
//     this.ocrService.processDocument(this.document.id, this.selectedEngine).subscribe({
//       next: (result) => {
//         this.snackBar.open('OCR processing completed!', 'Close', { duration: 3000 });
//         this.processing = false;
//         // Reload document to get updated extracted text
//         this.loadDocument(this.document!.id);
//       },
//       error: (error) => {
//         console.error('OCR processing error:', error);
//         const message = error.error?.detail || 'OCR processing failed';
//         this.snackBar.open(message, 'Close', { duration: 5000 });
//         this.processing = false;
//       }
//     });
//   }
  
//   downloadDocument(): void {
//     if (!this.document) return;
    
//     this.documentService.downloadDocument(this.document.id).subscribe({
//       next: (blob) => {
//         const url = window.URL.createObjectURL(blob);
//         const link = window.document.createElement('a');
//         link.href = url;
//         link.download = this.document!.filename;
//         link.click();
//         window.URL.revokeObjectURL(url);
//         this.snackBar.open('Download started', 'Close', { duration: 2000 });
//       },
//       error: (error) => {
//         console.error('Download error:', error);
//         this.snackBar.open('Download failed', 'Close', { duration: 3000 });
//       }
//     });
//   }
  
//   deleteDocument(): void {
//     if (!this.document) return;
    
//     if (!confirm(`Are you sure you want to delete "${this.document.filename}"?`)) {
//       return;
//     }
    
//     this.documentService.deleteDocument(this.document.id).subscribe({
//       next: () => {
//         this.snackBar.open('Document deleted successfully', 'Close', { duration: 3000 });
//         this.router.navigate(['/documents']);
//       },
//       error: (error) => {
//         console.error('Delete error:', error);
//         this.snackBar.open('Failed to delete document', 'Close', { duration: 3000 });
//       }
//     });
//   }
  
//   goBack(): void {
//     this.router.navigate(['/documents']);
//   }
  
//   getStatusColor(status: string): string {
//     switch (status) {
//       case 'completed': return 'primary';
//       case 'processing': return 'accent';
//       case 'failed': return 'warn';
//       default: return '';
//     }
//   }
  
//   formatFileSize(bytes: number): string {
//     if (bytes === 0) return '0 Bytes';
//     const k = 1024;
//     const sizes = ['Bytes', 'KB', 'MB', 'GB'];
//     const i = Math.floor(Math.log(bytes) / Math.log(k));
//     return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
//   }
  
//   formatDate(dateString: string): string {
//     const date = new Date(dateString);
//     return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
//   }
// }

// frontend/src/app/features/documents/document-detail/document-detail.component.ts

import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { MatStepperModule } from '@angular/material/stepper';
import { FormsModule } from '@angular/forms';
import { DocumentService } from '../../../core/services/document';
import { OcrService } from '../../../core/services/ocr';
import { Document } from '../../../core/models/document.model';

@Component({
  selector: 'app-document-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatSnackBarModule,
    MatDividerModule,
    MatSelectModule,
    MatTabsModule,
    MatStepperModule
  ],
  templateUrl: './document-detail.html',
  styleUrls: ['./document-detail.scss']
})
export class DocumentDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private documentService = inject(DocumentService);
  private ocrService = inject(OcrService);
  private snackBar = inject(MatSnackBar);

  document: Document | null = null;
  loading = true;
  processingOCR = false;
  processingLLM = false;
  selectedEngine: 'tesseract' | 'easyocr' | 'both' = 'tesseract';

  // Results
  rawText: string | null = null;
  llmResult: any = null;

  ngOnInit(): void {
    const documentId = this.route.snapshot.paramMap.get('id');
    if (documentId) {
      this.loadDocument(documentId);
    }
  }

  loadDocument(id: string): void {
    this.loading = true;
    this.documentService.getDocument(id).subscribe({
      next: (doc) => {
        this.document = doc;
        this.rawText = doc.extracted_text || null;
        this.loading = false;

        // Auto-load LLM result if already processed
        if (doc.status === 'completed' && this.rawText) {
          this.loadLLMResult(doc.id);
        }
      },
      error: () => {
        this.snackBar.open('Failed to load document', 'Close', { duration: 3000 });
        this.loading = false;
        this.router.navigate(['/documents']);
      }
    });
  }

  loadLLMResult(id: string): void {
    this.ocrService.getLLMResult(id).subscribe({
      next: (result) => {
        this.llmResult = result.extracted_fields;
      },
      error: () => {
        // No LLM result yet — that's fine
        this.llmResult = null;
      }
    });
  }

  // ── STEP 1: Run OCR ──────────────────────────────────────────────────────
  runOCR(): void {
    if (!this.document) return;
    this.processingOCR = true;

    this.ocrService.processDocument(this.document.id, this.selectedEngine).subscribe({
      next: (result) => {
        this.rawText = result.extracted_text || result.extracted_text || null;
        this.snackBar.open('✅ OCR complete — raw text extracted', 'Close', { duration: 3000 });
        this.processingOCR = false;
        this.loadDocument(this.document!.id);
      },
      error: (error) => {
        const message = error.error?.detail || 'OCR processing failed';
        this.snackBar.open(message, 'Close', { duration: 5000 });
        this.processingOCR = false;
      }
    });
  }

  // ── STEP 2: Run LLM Extraction ───────────────────────────────────────────
  runLLMExtraction(): void {
    if (!this.document) return;
    this.processingLLM = true;
    this.llmResult = null;

    this.ocrService.extractWithLLM(this.document.id).subscribe({
      next: (result) => {
        this.llmResult = result.extracted_fields;
        this.snackBar.open('✅ AI extraction complete', 'Close', { duration: 3000 });
        this.processingLLM = false;
      },
      error: (error) => {
        const message = error.error?.detail || 'LLM extraction failed';
        this.snackBar.open(message, 'Close', { duration: 5000 });
        this.processingLLM = false;
      }
    });
  }

  // ── Helpers ──────────────────────────────────────────────────────────────
  get llmKeys(): string[] {
    if (!this.llmResult) return [];
    return Object.keys(this.llmResult).filter(k => k !== 'line_items' && k !== 'patient');
  }

  get lineItems(): any[] {
    return this.llmResult?.line_items || [];
  }

  formatValue(value: any): string {
    if (value === null || value === undefined) return '—';
    return String(value);
  }

  goBack(): void {
    this.router.navigate(['/documents']);
  }

  deleteDocument(): void {
    if (!this.document) return;
    if (!confirm(`Delete "${this.document.filename}"?`)) return;

    this.documentService.deleteDocument(this.document.id).subscribe({
      next: () => {
        this.snackBar.open('Document deleted', 'Close', { duration: 3000 });
        this.router.navigate(['/documents']);
      },
      error: () => this.snackBar.open('Delete failed', 'Close', { duration: 3000 })
    });
  }
}