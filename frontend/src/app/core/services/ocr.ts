// frontend/src/app/core/services/ocr.service.ts

import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { OCRResult } from '../models/document.model';

@Injectable({
  providedIn: 'root'
})
export class OcrService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/ocr`;
  
  processDocument(documentId: string, engine: 'tesseract' | 'easyocr' | 'both' = 'tesseract'): Observable<OCRResult> {
    const params = new HttpParams().set('engine', engine);
    
    return this.http.post<OCRResult>(`${this.apiUrl}/process/${documentId}`, null, { params });
  }
  
  getOCRResult(documentId: string): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/result/${documentId}`);
  }
}