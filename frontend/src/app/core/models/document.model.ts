// frontend/src/app/core/models/document.model.ts

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  uploaded_at: string;
  extracted_text?: string;
  // Phase 2 additions
  document_type?: string;
  classification_confidence?: number;
  entities?: ExtractedEntities;
  tables?: DocumentTable[];
  json_output_path?: string;
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

// Phase 2 interfaces
export interface ExtractedEntities {
  persons?: string[];
  organizations?: string[];
  locations?: string[];
  dates?: string[];
  money?: string[];
  emails?: string[];
  phone_numbers?: string[];
  invoice_numbers?: string[];
  key_value_pairs?: { [key: string]: string };
}

export interface DocumentTable {
  headers: string[];
  rows: string[][];
  row_count: number;
  column_count: number;
  page?: number;
  table_number?: number;
  sheet_name?: string;
}

export interface AdvancedOCRResult {
  document_id: string;
  status: string;
  extracted_text: string;
  document_type: string;
  classification_confidence: number;
  entities_count: {
    persons: number;
    organizations: number;
    dates: number;
    monetary_values: number;
    emails: number;
    phone_numbers: number;
  };
  tables_count: number;
  json_output?: any;
  message: string;
}