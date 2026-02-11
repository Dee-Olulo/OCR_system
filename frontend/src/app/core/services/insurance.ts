// frontend/src/app/core/services/insurance.service.ts

import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { InsuranceClaimView, BatchInsuranceView } from '../models/insurance.model';

@Injectable({
  providedIn: 'root'
})
export class InsuranceService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/insurance`;
  
  /**
   * Get insurance claim view for a single document
   */
  getInsuranceView(documentId: string): Observable<InsuranceClaimView> {
    return this.http.get<InsuranceClaimView>(`${this.apiUrl}/view/${documentId}`);
  }
  
  /**
   * Get insurance claim view for multiple documents (batch)
   */
  getBatchInsuranceView(skip: number = 0, limit: number = 10): Observable<BatchInsuranceView> {
    return this.http.get<BatchInsuranceView>(`${this.apiUrl}/batch-view`, {
      params: { skip: skip.toString(), limit: limit.toString() }
    });
  }
}