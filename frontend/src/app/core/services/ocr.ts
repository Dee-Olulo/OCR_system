// frontend/src/app/core/services/ocr.service.ts

import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { OCRResult, AdvancedOCRResult } from '../models/document.model';

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
  
  // Phase 2: Advanced processing
  processDocumentAdvanced(
    documentId: string,
    options: {
      engine?: 'tesseract' | 'easyocr' | 'both';
      extractEntities?: boolean;
      extractTables?: boolean;
      classifyDocument?: boolean;
      generateJson?: boolean;
    } = {}
  ): Observable<AdvancedOCRResult> {
    let params = new HttpParams()
      .set('engine', options.engine || 'tesseract')
      .set('extract_entities', options.extractEntities !== false)
      .set('extract_tables', options.extractTables !== false)
      .set('classify_document', options.classifyDocument !== false)
      .set('generate_json', options.generateJson !== false);
    
    return this.http.post<AdvancedOCRResult>(
      `${this.apiUrl}/process-advanced/${documentId}`,
      null,
      { params }
    );
  }
  
  getAdvancedResult(documentId: string): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/result-advanced/${documentId}`);
  }
  
  downloadJson(documentId: string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/download-json/${documentId}`, {
      responseType: 'blob'
    });
  }
}