// // frontend/src/app/features/insurance/insurance-claim-view.component.ts

// import { Component, OnInit, inject } from '@angular/core';
// import { CommonModule } from '@angular/common';
// import { ActivatedRoute, Router } from '@angular/router';
// import { MatCardModule } from '@angular/material/card';
// import { MatButtonModule } from '@angular/material/button';
// import { MatIconModule } from '@angular/material/icon';
// import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
// import { MatChipsModule } from '@angular/material/chips';
// import { MatTableModule } from '@angular/material/table';
// import { MatDividerModule } from '@angular/material/divider';
// import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
// import { MatTooltipModule } from '@angular/material/tooltip';
// import { InsuranceService } from '../../core/services/insurance';
// import { InsuranceClaimView } from '../../core/models/insurance.model';

// @Component({
//   selector: 'app-insurance-claim-view',
//   standalone: true,
//   imports: [
//     CommonModule,
//     MatCardModule,
//     MatButtonModule,
//     MatIconModule,
//     MatProgressSpinnerModule,
//     MatChipsModule,
//     MatTableModule,
//     MatDividerModule,
//     MatSnackBarModule,
//     MatTooltipModule
//   ],
//   templateUrl: './insurance-claim-view.html',
//   styleUrls: ['./insurance-claim-view.scss']
// })
// export class InsuranceClaimViewComponent implements OnInit {
//   private route = inject(ActivatedRoute);
//   private router = inject(Router);
//   private insuranceService = inject(InsuranceService);
//   private snackBar = inject(MatSnackBar);
  
//   claimData: InsuranceClaimView | null = null;
//   loading = true;
//   error: string | null = null;
  
//   displayedColumns: string[] = ['description', 'quantity', 'unit_price', 'total'];
  
//   ngOnInit(): void {
//     const documentId = this.route.snapshot.paramMap.get('id');
//     if (documentId) {
//       this.loadInsuranceView(documentId);
//     } else {
//       this.error = 'No document ID provided';
//       this.loading = false;
//     }
//   }
  
//   loadInsuranceView(documentId: string): void {
//     this.loading = true;
//     this.error = null;
    
//     this.insuranceService.getInsuranceView(documentId).subscribe({
//       next: (data) => {
//         this.claimData = data;
//         this.loading = false;
//         console.log('Insurance claim data loaded:', data);
//       },
//       error: (err) => {
//         console.error('Error loading insurance view:', err);
//         this.error = err.error?.detail || 'Failed to load insurance claim view';
//         this.loading = false;
//         this.snackBar.open('Failed to load insurance claim view', 'Close', { duration: 5000 });
//       }
//     });
//   }
  
//   goBack(): void {
//     this.router.navigate(['/documents']);
//   }
  
//   viewFullDocument(): void {
//     if (this.claimData?.document_info?.document_id) {
//       this.router.navigate(['/documents', this.claimData.document_info.document_id]);
//     }
//   }
  
//   exportToPDF(): void {
//     // TODO: Implement PDF export
//     this.snackBar.open('PDF export coming soon', 'Close', { duration: 3000 });
//   }
  
//   exportToExcel(): void {
//     // TODO: Implement Excel export
//     this.snackBar.open('Excel export coming soon', 'Close', { duration: 3000 });
//   }
  
//   submitToClearinghouse(): void {
//     // TODO: Implement clearinghouse submission
//     this.snackBar.open('Clearinghouse submission coming soon', 'Close', { duration: 3000 });
//   }
  
//   getQualityColor(): string {
//     if (!this.claimData?.raw_confidence) return '';
    
//     const quality = this.claimData.raw_confidence.extraction_quality;
//     switch (quality) {
//       case 'excellent': return 'primary';
//       case 'good': return 'accent';
//       case 'fair': return 'warn';
//       case 'poor': return 'warn';
//       default: return '';
//     }
//   }
  
//   getQualityIcon(): string {
//     if (!this.claimData?.raw_confidence) return 'help';
    
//     const quality = this.claimData.raw_confidence.extraction_quality;
//     switch (quality) {
//       case 'excellent': return 'check_circle';
//       case 'good': return 'check_circle_outline';
//       case 'fair': return 'warning';
//       case 'poor': return 'error';
//       default: return 'help';
//     }
//   }
  
//   hasValue(value: any): boolean {
//     return value !== null && value !== undefined && value !== '';
//   }
  
//   formatDate(dateString: string | undefined): string {
//     if (!dateString) return 'N/A';
//     try {
//       const date = new Date(dateString);
//       return date.toLocaleDateString();
//     } catch {
//       return dateString;
//     }
//   }
  
//   getMissingFieldsCount(): number {
//     return this.claimData?.raw_confidence?.missing_critical_fields?.length || 0;
//   }
// }
// frontend/src/app/features/insurance/insurance-claim-view.component.ts

import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatTableModule } from '@angular/material/table';
import { MatDividerModule } from '@angular/material/divider';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { InsuranceService } from '../../core/services/insurance';
import { InsuranceClaimView } from '../../core/models/insurance.model';

@Component({
  selector: 'app-insurance-claim-view',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTableModule,
    MatDividerModule,
    MatSnackBarModule,
    MatTooltipModule
  ],
  templateUrl: './insurance-claim-view.html',
  styleUrls: ['./insurance-claim-view.scss']
})
export class InsuranceClaimViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private insuranceService = inject(InsuranceService);
  private snackBar = inject(MatSnackBar);
  
  claimData: InsuranceClaimView | null = null;
  loading = true;
  error: string | null = null;
  
  displayedColumns: string[] = ['description', 'quantity', 'unit_price', 'total'];
  
  ngOnInit(): void {
    const documentId = this.route.snapshot.paramMap.get('id');
    if (documentId) {
      this.loadInsuranceView(documentId);
    } else {
      this.error = 'No document ID provided';
      this.loading = false;
    }
  }
  
  loadInsuranceView(documentId: string): void {
    this.loading = true;
    this.error = null;
    
    this.insuranceService.getInsuranceView(documentId).subscribe({
      next: (data) => {
        this.claimData = data;
        this.loading = false;
        console.log('Insurance claim data loaded:', data);
      },
      error: (err) => {
        console.error('Error loading insurance view:', err);
        this.error = err.error?.detail || 'Failed to load insurance claim view';
        this.loading = false;
        this.snackBar.open('Failed to load insurance claim view', 'Close', { duration: 5000 });
      }
    });
  }
  
  goBack(): void {
    this.router.navigate(['/documents']);
  }
  
  viewFullDocument(): void {
    if (this.claimData?.document_info?.document_id) {
      this.router.navigate(['/documents', this.claimData.document_info.document_id]);
    }
  }
  
  exportToPDF(): void {
    // TODO: Implement PDF export
    this.snackBar.open('PDF export coming soon', 'Close', { duration: 3000 });
  }
  
  exportToExcel(): void {
    // TODO: Implement Excel export
    this.snackBar.open('Excel export coming soon', 'Close', { duration: 3000 });
  }
  
  submitToClearinghouse(): void {
    // TODO: Implement clearinghouse submission
    this.snackBar.open('Clearinghouse submission coming soon', 'Close', { duration: 3000 });
  }
  
  getQualityColor(): string {
    if (!this.claimData?.raw_confidence) return '';
    
    const quality = this.claimData.raw_confidence.extraction_quality;
    switch (quality) {
      case 'excellent': return 'primary';
      case 'good': return 'accent';
      case 'fair': return 'warn';
      case 'poor': return 'warn';
      default: return '';
    }
  }
  
  getQualityIcon(): string {
    if (!this.claimData?.raw_confidence) return 'help';
    
    const quality = this.claimData.raw_confidence.extraction_quality;
    switch (quality) {
      case 'excellent': return 'check_circle';
      case 'good': return 'check_circle_outline';
      case 'fair': return 'warning';
      case 'poor': return 'error';
      default: return 'help';
    }
  }
  
  hasValue(value: any): boolean {
    return value !== null && value !== undefined && value !== '';
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
  
  getMissingFieldsCount(): number {
    return this.claimData?.raw_confidence?.missing_critical_fields?.length || 0;
  }
}