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
import { MatTableModule } from '@angular/material/table';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FormsModule } from '@angular/forms';
import { DocumentService } from '../../../core/services/document';
import { OcrService } from '../../../core/services/ocr';
import { Document, ExtractedEntities, DocumentTable } from '../../../core/models/document.model';

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
    MatTableModule,
    MatExpansionModule,
    MatCheckboxModule,
    MatTooltipModule
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
  processing = false;
  selectedEngine: 'tesseract' | 'easyocr' | 'both' = 'tesseract';
  
  // Phase 2 properties
  useAdvancedProcessing = true;
  extractEntities = true;
  extractTables = true;
  classifyDocument = true;
  generateJson = true;
  
  // JSON output
  jsonOutput: any = null;
  
  ngOnInit(): void {
    const documentId = this.route.snapshot.paramMap.get('id');
    if (documentId) {
      this.loadDocument(documentId);
    }
  }
  
  loadDocument(id: string): void {
    this.loading = true;
    
    this.documentService.getDocument(id).subscribe({
      next: (document) => {
        this.document = document;
        this.loading = false;
        
        // ALWAYS try to load JSON for completed documents
        if (document.status === 'completed') {
          this.loadJsonOutput();
        } else {
          this.jsonOutput = null;
        }
      },
      error: (error) => {
        console.error('Error loading document:', error);
        this.snackBar.open('Failed to load document', 'Close', { duration: 3000 });
        this.loading = false;
        this.router.navigate(['/documents']);
      }
    });
  }
  
  loadJsonOutput(): void {
    if (!this.document) return;
    
    // Fetch the advanced result which includes JSON output
    this.ocrService.getAdvancedResult(this.document.id).subscribe({
      next: (result) => {
        // Use the JSON output from backend if available
        if (result.json_output) {
          this.jsonOutput = result.json_output;
        } else {
          // Fallback: build from document data
          this.jsonOutput = this.buildJsonFromDocument();
        }
      },
      error: (error) => {
        console.log('Advanced result not available, building from document data');
        this.jsonOutput = this.buildJsonFromDocument();
      }
    });
  }
  
  buildJsonFromDocument(): any {
    if (!this.document) return null;
    
    const output: any = {
      document_info: {
        filename: this.document.filename,
        file_type: this.document.file_type,
        document_type: this.document.document_type || 'unknown',
        classification_confidence: this.document.classification_confidence || 0,
        uploaded_at: this.document.uploaded_at,
        status: this.document.status
      }
    };
    
    // Add entities if available
    if (this.document.entities) {
      output.entities = this.document.entities;
    }
    
    // Add tables if available
    if (this.document.tables && this.document.tables.length > 0) {
      output.tables = this.document.tables;
    }
    
    // Add extracted text
    if (this.document.extracted_text) {
      output.extracted_text = this.document.extracted_text.substring(0, 500) + '...'; // First 500 chars
    }
    
    return output;
  }
  
  processWithOCR(): void {
    if (!this.document) return;
    
    this.processing = true;
    
    // Check if we should use advanced processing (Phase 2)
    const isPdfOrOffice = this.document.file_type.includes('pdf') || 
                          this.document.file_type.includes('word') ||
                          this.document.file_type.includes('document') ||
                          this.document.file_type.includes('spreadsheet') ||
                          this.document.file_type.includes('presentation');
    
    if (this.useAdvancedProcessing || isPdfOrOffice) {
      // Use Phase 2 advanced processing
      this.ocrService.processDocumentAdvanced(this.document.id, {
        engine: this.selectedEngine,
        extractEntities: this.extractEntities,
        extractTables: this.extractTables,
        classifyDocument: this.classifyDocument,
        generateJson: this.generateJson
      }).subscribe({
        next: (result) => {
          this.snackBar.open(`Processing completed! Document type: ${result.document_type}`, 'Close', { duration: 3000 });
          this.processing = false;
          this.loadDocument(this.document!.id);
        },
        error: (error) => {
          console.error('OCR processing error:', error);
          const message = error.error?.detail || 'OCR processing failed';
          this.snackBar.open(message, 'Close', { duration: 5000 });
          this.processing = false;
        }
      });
    } else {
      // Use basic OCR (Phase 1)
      this.ocrService.processDocument(this.document.id, this.selectedEngine).subscribe({
        next: (result) => {
          this.snackBar.open('OCR processing completed!', 'Close', { duration: 3000 });
          this.processing = false;
          this.loadDocument(this.document!.id);
        },
        error: (error) => {
          console.error('OCR processing error:', error);
          const message = error.error?.detail || 'OCR processing failed';
          this.snackBar.open(message, 'Close', { duration: 5000 });
          this.processing = false;
        }
      });
    }
  }
  
  downloadDocument(): void {
    if (!this.document) return;
    
    this.documentService.downloadDocument(this.document.id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = window.document.createElement('a');
        link.href = url;
        link.download = this.document!.filename;
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
  
  deleteDocument(): void {
    if (!this.document) return;
    
    if (!confirm(`Are you sure you want to delete "${this.document.filename}"?`)) {
      return;
    }
    
    this.documentService.deleteDocument(this.document.id).subscribe({
      next: () => {
        this.snackBar.open('Document deleted successfully', 'Close', { duration: 3000 });
        this.router.navigate(['/documents']);
      },
      error: (error) => {
        console.error('Delete error:', error);
        this.snackBar.open('Failed to delete document', 'Close', { duration: 3000 });
      }
    });
  }
  
  downloadJson(): void {
    if (!this.document) return;
    
    this.ocrService.downloadJson(this.document.id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = window.document.createElement('a');
        link.href = url;
        link.download = `${this.document!.filename}_output.json`;
        link.click();
        window.URL.revokeObjectURL(url);
        this.snackBar.open('JSON downloaded', 'Close', { duration: 2000 });
      },
      error: (error) => {
        console.error('JSON download error:', error);
        this.snackBar.open('JSON output not available', 'Close', { duration: 3000 });
      }
    });
  }
  
  goBack(): void {
    this.router.navigate(['/documents']);
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
  
  // Phase 2 helper methods
  hasAnyEntities(): boolean {
    if (!this.document?.entities) {
      return false;
    }
    
    const entities = this.document.entities;
    
    const hasPersons = entities.persons ? entities.persons.length > 0 : false;
    const hasOrgs = entities.organizations ? entities.organizations.length > 0 : false;
    const hasMoney = entities.money ? entities.money.length > 0 : false;
    const hasEmails = entities.emails ? entities.emails.length > 0 : false;
    const hasPhones = entities.phone_numbers ? entities.phone_numbers.length > 0 : false;
    const hasKvPairs = entities.key_value_pairs ? Object.keys(entities.key_value_pairs).length > 0 : false;
    
    return hasPersons || hasOrgs || hasMoney || hasEmails || hasPhones || hasKvPairs;
  }
  
  Object = Object; // Make Object available in template
  
  getFormattedJson(): string {
    if (!this.jsonOutput) {
      return 'Loading...';
    }
    return JSON.stringify(this.jsonOutput, null, 2);
  }
  
  copyJsonToClipboard(): void {
    const jsonText = this.getFormattedJson();
    navigator.clipboard.writeText(jsonText).then(() => {
      this.snackBar.open('JSON copied to clipboard!', 'Close', { duration: 2000 });
    }).catch(err => {
      console.error('Failed to copy:', err);
      this.snackBar.open('Failed to copy JSON', 'Close', { duration: 2000 });
    });
  }
}