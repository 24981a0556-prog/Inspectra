// INSPECTRA TypeScript type definitions — mirrors backend Pydantic schemas

export type UserRole = 'INSPECTOR' | 'SUPERVISOR' | 'ADMIN';

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  user: User;
}

export type InspectionStatus =
  | 'DRAFT'
  | 'IN_PROGRESS'
  | 'ANALYZING'
  | 'COMPLETED'
  | 'REQUIRES_REVIEW'
  | 'CLOSED';

export type FinalDecision =
  | 'COMPLIANT'
  | 'NON_COMPLIANT'
  | 'REQUIRES_FURTHER_REVIEW';

export type ViewType = 'FRONT' | 'BACK' | 'LEFT' | 'RIGHT' | 'TOP' | 'BOTTOM' | 'OTHER';

export type ComplianceStatus =
  | 'NOT_CHECKED'
  | 'PROCESSING'
  | 'PASS'
  | 'FAIL'
  | 'NEEDS_VERIFICATION'
  | 'NOT_APPLICABLE';

export type ComplianceSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface Product {
  id: number;
  product_code: string;
  product_name: string;
  category: string | null;
  manufacturer: string | null;
  created_at: string;
}

export interface InspectionImage {
  id: number;
  inspection_id: number;
  image_url: string;
  view_type: ViewType;
  original_filename: string | null;
  created_at: string;
}

export interface Inspection {
  id: number;
  inspection_number: string;
  product_id: number;
  inspector_id: number;
  status: InspectionStatus;
  notes: string | null;
  is_demo: boolean;
  final_decision: FinalDecision | null;
  finalized_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface InspectionDetail extends Inspection {
  product: Product;
  inspector: User;
  images: InspectionImage[];
  final_decision_comment: string | null;
  analysis_error: string | null;
}

export interface DashboardStats {
  total_inspections: number;
  by_status: Record<InspectionStatus, number>;
  total_products: number;
  total_inspectors: number;
}

// ── Analysis Pipeline Types ───────────────────────────────────────────────

export interface AnalysisStatus {
  inspection_id: number;
  status: InspectionStatus;
  analysis_error: string | null;
  ai_results_count: number;
  evidence_count: number;
  compliance_checks_count: number;
}

export interface AIResult {
  id: number;
  inspection_id: number;
  agent_type: 'label_agent' | 'quantity_agent' | 'declaration_agent';
  result_json: Record<string, any> | null;
  confidence: number | null;
  model_name: string | null;
  model_version: string | null;
  provider: string | null;
  created_at: string;
}

export interface Evidence {
  id: number;
  inspection_id: number;
  image_id: number | null;
  evidence_ref_id: string | null;  // "EV-001"
  agent_type: string | null;
  evidence_type: string | null;
  field_name: string | null;
  extracted_value: string | null;
  confidence: number | null;
  ocr_text: string | null;
  extra_data: Record<string, any> | null;
  created_at: string;
}

export interface ComplianceCheck {
  id: number;
  inspection_id: number;
  rule_id: string;
  rule_name: string | null;
  engine_type: string | null;
  status: ComplianceStatus;
  severity: ComplianceSeverity | null;
  message: string | null;
  confidence: number | null;
  evidence_ref_ids: string[];
  requires_human_review: boolean;
  human_reviewed: boolean;
  human_action: string | null;
  human_comment: string | null;
  created_at: string;
}

export interface ApiError {
  detail: string;
}
