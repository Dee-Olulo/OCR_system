// // frontend/src/app/core/models/insurance.model.ts

// export interface InsuranceClaimView {
//   patient_info: PatientInfo;
//   provider_info: ProviderInfo;
//   financial_info: FinancialInfo;
//   clinical_info: ClinicalInfo;
//   line_items: LineItem[];
//   raw_confidence: QualityAssessment;
//   document_info?: DocumentInfo;
//   extraction_timestamp?: string;
//   document_type?: string;
//   language?: string;
// }

// export interface PatientInfo {
//   full_name?: string;
//   patient_id?: string;
//   date_of_birth?: string;
//   insurance_policy_number?: string;
// }

// export interface ProviderInfo {
//   hospital_name?: string;
//   provider_npi?: string;
//   department?: string;
//   doctor_name?: string;
// }

// export interface FinancialInfo {
//   invoice_number?: string;
//   invoice_date?: string;
//   total_amount?: string;
//   currency?: string;
// }

// export interface ClinicalInfo {
//   admission_date?: string;
//   discharge_date?: string;
//   diagnosis?: string;
//   diagnosis_codes?: string[];
//   procedure_codes?: string[];
// }

// export interface LineItem {
//   description: string;
//   quantity?: string;
//   unit_price?: string;
//   total?: string;
// }

// export interface QualityAssessment {
//   extraction_quality: 'excellent' | 'good' | 'fair' | 'poor' | 'unknown';
//   completeness_percentage?: number;
//   critical_fields_found?: number;
//   critical_fields_total?: number;
//   missing_critical_fields?: string[];
//   ocr_confidence?: number;
//   has_line_items?: boolean;
// }

// export interface DocumentInfo {
//   document_id: string;
//   filename: string;
//   upload_date?: string;
//   processed_date?: string;
//   ocr_engine?: string;
// }

// export interface BatchInsuranceView {
//   claims: InsuranceClaimView[];
//   total: number;          // Total number of documents available
//   skip: number;           // Pagination skip
//   limit: number;          // Pagination limit  
//   count: number;          // Number of documents in current page
// }

// frontend/src/app/core/models/insurance.model.ts

export interface InsuranceClaimView {
  patient_info: PatientInfo;
  provider_info: ProviderInfo;
  financial_info: FinancialInfo;
  clinical_info: ClinicalInfo;
  line_items: LineItem[];
  raw_confidence: QualityAssessment;
  document_info?: DocumentInfo;
  extraction_timestamp?: string;
  document_type?: string;
  language?: string;
}

export interface PatientInfo {
  full_name?: string;
  patient_id?: string;
}

export interface ProviderInfo {
  hospital_name?: string;
  provider_npi?: string;
  department?: string;
  doctor_name?: string;
}

export interface FinancialInfo {
  invoice_number?: string;
  invoice_date?: string;
  total_amount?: string;
  amount_due?: string;
  currency?: string;
}

export interface ClinicalInfo {
  admission_date?: string;
  discharge_date?: string;
  diagnosis?: string;
  diagnosis_codes?: string[];
  procedure_codes?: string[];
}

export interface LineItem {
  description: string;
  quantity?: string;
  unit_price?: string;
  total?: string;
}

export interface QualityAssessment {
  extraction_quality: 'excellent' | 'good' | 'fair' | 'poor' | 'unknown';
  completeness_percentage?: number;
  critical_fields_found?: number;
  critical_fields_total?: number;
  missing_critical_fields?: string[];
  ocr_confidence?: number;
  has_line_items?: boolean;
}

export interface DocumentInfo {
  document_id: string;
  filename: string;
  upload_date?: string;
  processed_date?: string;
  ocr_engine?: string;
}

export interface BatchInsuranceView {
  total_processed: number;
  skip: number;
  limit: number;
  claims: InsuranceClaimView[];
}