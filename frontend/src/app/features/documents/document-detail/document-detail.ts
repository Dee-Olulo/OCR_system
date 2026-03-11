// frontend/src/app/features/documents/document-detail/document-detail.component.ts

import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MatBadgeModule } from '@angular/material/badge';
import { interval, Subscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { DocumentService } from '../../../core/services/document';
import { OcrService } from '../../../core/services/ocr';
import { Document } from '../../../core/models/document.model';

type PipelineStatus = 'pending' | 'ocr' | 'extraction' | 'complete' | 'failed' | 'review';

@Component({
  selector: 'app-document-detail',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatSnackBarModule,
    MatDividerModule,
    MatTooltipModule,
    MatTabsModule,
    MatBadgeModule,
  ],
  templateUrl: './document-detail.html',
  styleUrls: ['./document-detail.scss']
})
export class DocumentDetailComponent implements OnInit, OnDestroy {
  private route           = inject(ActivatedRoute);
  private router          = inject(Router);
  private documentService = inject(DocumentService);
  private ocrService      = inject(OcrService);
  private snackBar        = inject(MatSnackBar);

  document: Document | null = null;
  loading = true;

  // Pipeline data
  rawText: string | null = null;
  canonicalFields: any   = null;
  normalizedFields: any  = null;
  mappedFields: any      = null;
  insurerKey: string | null        = null;
  insurerDisplayName: string | null = null;
  extractionComplete = false;
  confidenceScore: number | null = null;
  confidenceLevel: 'high' | 'medium' | 'low' | null = null;
  tableValidation: any  = null;
  missingFields: string[] = [];
  auditLog: any[]        = [];

  // UI state
  pipelineStatus: PipelineStatus = 'pending';
  pollingActive = false;
  showDebug = false;

  private pollSub?: Subscription;

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) this.loadDocument(id);
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
  }

  // ── Data loading ──────────────────────────────────────────────────────────

  loadDocument(id: string): void {
    this.loading = true;
    this.documentService.getDocument(id).subscribe({
      next: (doc) => {
        this.document = doc;
        this.loading  = false;
        this.syncPipelineStatus(doc);

        if (doc.status === 'completed' || doc.status === 'processing') {
          this.loadLLMResult(doc.id);
        }

        // Auto-poll while pipeline is running
        if (doc.status === 'pending' || doc.status === 'processing') {
          this.startPolling(doc.id);
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
      error: () => {}
    });
  }

  startPolling(id: string): void {
    if (this.pollingActive) return;
    this.pollingActive = true;

    this.pollSub = interval(4000).pipe(
      switchMap(() => this.documentService.getDocument(id)),
      takeWhile(doc => doc.status === 'pending' || doc.status === 'processing', true)
    ).subscribe({
      next: (doc) => {
        this.document = doc;
        this.syncPipelineStatus(doc);
        if (doc.status === 'completed') {
          this.loadLLMResult(doc.id);
          this.pollingActive = false;
        }
        if (doc.status === 'failed') {
          this.pollingActive = false;
        }
      },
      error: () => { this.pollingActive = false; }
    });
  }

  // ── State sync ────────────────────────────────────────────────────────────

  syncPipelineStatus(doc: Document): void {
    if (doc.status === 'pending')    this.pipelineStatus = 'pending';
    if (doc.status === 'processing') this.pipelineStatus = 'ocr';
    if (doc.status === 'completed')  this.pipelineStatus = this.mappedFields ? 'complete' : 'extraction';
    if (doc.status === 'failed')     this.pipelineStatus = 'failed';
  }

  private applyLLMResult(result: any): void {
    this.canonicalFields    = result.canonical_fields  || result.extracted_fields || null;
    this.normalizedFields   = result.normalized_fields || null;
    this.mappedFields       = result.mapped_fields     || null;
    this.insurerKey         = result.insurer           || null;
    this.insurerDisplayName = result.insurer_display_name || null;
    this.extractionComplete = result.extraction_complete ?? false;
    this.tableValidation    = result.table_validation  || null;
    this.missingFields      = result.missing_required_fields || [];
    this.rawText            = this.document?.extracted_text || null;

    if (this.mappedFields || this.canonicalFields) {
      this.pipelineStatus = 'complete';
    }
  }

  // ── Computed props ────────────────────────────────────────────────────────

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

  get isProcessing(): boolean {
    return this.pipelineStatus === 'pending' || this.pipelineStatus === 'ocr' || this.pipelineStatus === 'extraction';
  }

  get confidenceBadgeClass(): string {
    switch (this.confidenceLevel) {
      case 'high':   return 'confidence-high';
      case 'medium': return 'confidence-medium';
      case 'low':    return 'confidence-low';
      default:       return '';
    }
  }

  get pipelineSteps() {
    return [
      {
        id: 'received',
        label: 'Received',
        sublabel: 'File saved to server',
        icon: 'inbox',
        done: true,
        active: false,
      },
      {
        id: 'ocr',
        label: 'OCR Extraction',
        sublabel: 'Tesseract text extraction',
        icon: 'document_scanner',
        done: !!this.rawText,
        active: this.pipelineStatus === 'ocr',
      },
      {
        id: 'llm',
        label: 'AI Extraction',
        sublabel: 'Llama 3 field extraction',
        icon: 'psychology',
        done: !!this.canonicalFields,
        active: this.pipelineStatus === 'extraction',
      },
      {
        id: 'mapping',
        label: 'Schema Mapping',
        sublabel: 'Insurer normalization',
        icon: 'swap_horiz',
        done: !!this.mappedFields,
        active: false,
      },
      {
        id: 'confidence',
        label: 'Quality Gate',
        sublabel: 'Confidence scoring',
        icon: 'verified',
        done: this.pipelineStatus === 'complete',
        active: false,
      },
    ];
  }

  get tableMatchStatus(): string {
    if (!this.tableValidation) return 'unknown';
    return this.tableValidation.total_match ? 'match' : 'mismatch';
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  formatValue(value: any): string {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'number') return value.toLocaleString();
    return String(value);
  }

  formatKey(key: string): string {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  formatFileSize(bytes: number): string {
    if (!bytes) return '0 B';
    const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
  }

  goBack(): void { this.router.navigate(['/documents']); }

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

  copyToClipboard(data: any): void {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    this.snackBar.open('Copied to clipboard', '', { duration: 2000 });
  }
}