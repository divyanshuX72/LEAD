export interface LeadBatch {
  id: string;
  name: string;
  location: string;
  requested_count: number;
  raw_results_count: number;
  duplicate_count: number;
  rejected_count: number;
  final_count: number;
  status: 'pending' | 'running' | 'partial' | 'completed' | 'failed' | 'cancelled';
  reason: string | null;
  keywords: string[];
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Lead {
  id: string;
  batch_id: string;
  business_name: string;
  contact_name: string | null;
  designation: string | null;
  emails: string[];
  phones: string[];
  website: string | null;
  linkedin_url: string | null;
  instagram_url: string | null;
  facebook_url: string | null;
  x_url: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  matched_keyword: string | null;
  source_primary: string | null;
  source_url: string | null;
  rating: number | null;
  review_count: number | null;
  quality_status: 'valid' | 'suspect' | 'invalid';
  verification_status: 'unverified' | 'verified' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface ExportJob {
  id: string;
  export_type: 'csv' | 'xlsx';
  selection_type: 'single_batch' | 'selected_batches' | 'all';
  lead_count: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  file_name: string | null;
  created_at: string;
}

export interface DashboardStats {
  total_leads: number;
  total_batches: number;
  last_search: string | null;
  unique_emails: number;
  unique_phones: number;
}

export interface SearchProgress {
  batch_id: string;
  status: 'running' | 'completed' | 'failed' | 'partial' | 'stopped';
  current_keyword: string | null;
  keywords_completed: number;
  keywords_total: number;
  leads_found: number;
  leads_target: number;
  duplicates?: number;
  scanned?: number;
  message: string;
  reason?: string;
  retry_round?: number;
}
