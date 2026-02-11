// frontend/src/app/features/insurance/insurance-batch-view.component.ts

import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { InsuranceService } from '../../core/services/insurance';
import { InsuranceClaimView, BatchInsuranceView } from '../../core/models/insurance.model';

@Component({
  selector: 'app-insurance-batch-view',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatPaginatorModule,
    MatSnackBarModule,
    MatDividerModule
  ],
  templateUrl: './insurance-batch-view.html',
  styleUrls: ['./insurance-batch-view.scss']
})
export class InsuranceBatchViewComponent implements OnInit {
  private router = inject(Router);
  private insuranceService = inject(InsuranceService);
  private snackBar = inject(MatSnackBar);
  
  claims: InsuranceClaimView[] = [];
  loading = true;
  error: string | null = null;
  
  // Pagination
  pageSize = 10;
  pageIndex = 0;
  totalClaims = 0;
  
  ngOnInit(): void {
    this.loadBatchClaims();
  }
  
  loadBatchClaims(): void {
    this.loading = true;
    this.error = null;
    
    const skip = this.pageIndex * this.pageSize;
    
    this.insuranceService.getBatchInsuranceView(skip, this.pageSize).subscribe({
      next: (data: BatchInsuranceView) => {
        this.claims = data.claims;
        this.totalClaims = data.total_processed; // ← Fixed: was data.total_processed
        this.loading = false;
        console.log('Loaded claims:', data);
      },
      error: (err) => {
        console.error('Error loading batch claims:', err);
        this.error = err.error?.detail || 'Failed to load insurance claims';
        this.loading = false;
        this.snackBar.open("Failed to load insurance claims", 'Close', { duration: 5000 });
      }
    });
  }
  
  onPageChange(event: PageEvent): void {
    this.pageSize = event.pageSize;
    this.pageIndex = event.pageIndex;
    this.loadBatchClaims();
  }
  
  viewClaim(claim: InsuranceClaimView): void {
    if (claim.document_info?.document_id) {
      this.router.navigate(['/insurance/claim', claim.document_info.document_id]);
    }
  }
  
  getQualityColor(claim: InsuranceClaimView): string {
    const quality = claim.raw_confidence?.extraction_quality;
    switch (quality) {
      case 'excellent': return 'primary';
      case 'good': return 'accent';
      case 'fair': return 'warn';
      case 'poor': return 'warn';
      default: return '';
    }
  }
  
  getQualityIcon(claim: InsuranceClaimView): string {
    const quality = claim.raw_confidence?.extraction_quality;
    switch (quality) {
      case 'excellent': return 'check_circle';
      case 'good': return 'check_circle_outline';
      case 'fair': return 'warning';
      case 'poor': return 'error';
      default: return 'help';
    }
  }
  
  formatDate(dateString: string | undefined): string {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    } catch {
      return dateString;
    }
  }
  
  exportAll(): void {
    this.snackBar.open('Batch export coming soon', 'Close', { duration: 3000 });
  }
}