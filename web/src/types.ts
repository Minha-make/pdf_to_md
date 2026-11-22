export type ConversionMode = "auto" | "fast" | "deep";

export type JobStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "cancelled";

export interface Job {
  id: string;
  filename: string;
  sha256: string;
  status: JobStatus;
  mode: ConversionMode;
  current_page: number;
  total_pages: number;
  engine_used: string;
  markdown_path?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
  cached?: boolean;
}

export interface JobResult {
  job_id: string;
  filename: string;
  total_pages: number;
  engine_used: string;
  markdown: string;
  assets: string[];
  completed_at: string;
}

export interface SystemStatus {
  version: string;
  python_version: string;
  cpu_count: number;
  compute: {
    device: "cuda" | "cpu";
    cuda_available: boolean;
    device_name: string;
  };
  services: {
    ollama_online: boolean;
    ollama_url: string;
  };
  queue: {
    active_job_id: string | null;
    pending_count: number;
  };
}
