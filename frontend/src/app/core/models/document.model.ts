// frontend/src/app/core/models/document.model.ts

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  uploaded_at: string;
  extracted_text?: string;
}

export interface OCRResult {
  document_id: string;
  extracted_text: string;
  language: string;
  confidence_score: number;
  ocr_engine: string;
  processing_time: number;
}

export interface DocumentStats {
  total: number;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}