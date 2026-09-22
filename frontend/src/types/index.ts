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
  | 'COMPLETED'
  | 'REQUIRES_REVIEW'
  | 'CLOSED';

export type ViewType = 'FRONT' | 'BACK' | 'LEFT' | 'RIGHT' | 'TOP' | 'BOTTOM' | 'OTHER';

export type ComplianceStatus =
  | 'NOT_CHECKED'
  | 'PROCESSING'
  | 'PASS'
  | 'FAIL'
  | 'NEEDS_VERIFICATION'
  | 'NOT_APPLICABLE';

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
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface InspectionDetail extends Inspection {
  product: Product;
  inspector: User;
  images: InspectionImage[];
}

export interface DashboardStats {
  total_inspections: number;
  by_status: Record<InspectionStatus, number>;
  total_products: number;
  total_inspectors: number;
}

export interface ApiError {
  detail: string;
}
