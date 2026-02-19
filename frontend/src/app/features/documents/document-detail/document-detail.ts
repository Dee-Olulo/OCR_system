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
import { MatTooltipModule } from '@angular/material/tooltip';
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
    MatTooltipModule,
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

  // Step 1 — OCR
  rawText: string | null = null;

  // Step 2+3 — LLM + Mapping (Phase 3 response shape)
  canonicalFields: any = null;   // raw LLM output
  normalizedFields: any = null;  // after normalization
  mappedFields: any = null;      // insurer-specific field names
  insurerKey: string | null = null;
  insurerDisplayName: string | null = null;
  extractionComplete: boolean = false;
  // missingRequiredFields: string[] = [];

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
      next: (result) => this.applyLLMResult(result),
      error: () => {
        // No LLM result yet — fine, user hasn't run it
      }
    });
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  private applyLLMResult(result: any): void {
    // Phase 3 response shape from /llm/extract or /llm/result
    this.canonicalFields  = result.canonical_fields  || result.extracted_fields || null;
    this.normalizedFields = result.normalized_fields || null;
    this.mappedFields     = result.mapped_fields     || null;
    this.insurerKey       = result.insurer           || null;
    this.insurerDisplayName = result.insurer_display_name || null;
    this.extractionComplete = result.extraction_complete ?? false;
    // this.missingRequiredFields = result.missing_required_fields || [];
  }

  get mappedKeys(): string[] {
    if (!this.mappedFields) return [];
    return Object.keys(this.mappedFields).filter(k => k !== 'line_items');
  }

  get lineItems(): any[] {
    return this.mappedFields?.line_items || this.canonicalFields?.line_items || [];
  }

  get hasLLMResult(): boolean {
    return !!(this.mappedFields || this.canonicalFields);
  }

  formatValue(value: any): string {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'number') return value.toLocaleString();
    return String(value);
  }

  formatKey(key: string): string {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  // ── STEP 1: Run OCR ──────────────────────────────────────────────────────
  runOCR(): void {
    if (!this.document) return;
    this.processingOCR = true;

    this.ocrService.processDocument(this.document.id, this.selectedEngine).subscribe({
      next: (result) => {
        this.rawText = result.extracted_text || null;
        this.snackBar.open('✅ OCR complete', 'Close', { duration: 3000 });
        this.processingOCR = false;
        this.loadDocument(this.document!.id);
      },
      error: (error) => {
        this.snackBar.open(error.error?.detail || 'OCR failed', 'Close', { duration: 5000 });
        this.processingOCR = false;
      }
    });
  }

  // ── STEP 2+3: Run LLM + Mapping ──────────────────────────────────────────
  runLLMExtraction(): void {
    if (!this.document) return;
    this.processingLLM = true;
    this.canonicalFields = null;
    this.mappedFields = null;
    this.normalizedFields = null;

    this.ocrService.extractWithLLM(this.document.id).subscribe({
      next: (result) => {
        this.applyLLMResult(result);
        const msg = this.extractionComplete
          // ? '✅ Extraction complete — all required fields found'
          // : `⚠️ Extraction done — ${this.missingRequiredFields.length} required field(s) missing`;
        // this.snackBar.open(msg, 'Close', { duration: 4000 });
        this.processingLLM = false;
      },
      error: (error) => {
        this.snackBar.open(error.error?.detail || 'LLM extraction failed', 'Close', { duration: 5000 });
        this.processingLLM = false;
      }
    });
  }

  // ── Delete / Navigate ─────────────────────────────────────────────────────
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