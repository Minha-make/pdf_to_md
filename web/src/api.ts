import { Job, JobResult, SystemStatus } from "./types";

const BASE_URL = "/api";

export async function uploadJob(
  file: File,
  options: {
    mode?: string;
    password?: string;
    extractImages?: boolean;
    forceReconvert?: boolean;
  } = {}
): Promise<Job> {
  const formData = new FormData();
  formData.append("file", file);
  if (options.mode) formData.append("mode", options.mode);
  if (options.password) formData.append("password", options.password);
  formData.append("extract_images", options.extractImages !== false ? "true" : "false");
  if (options.forceReconvert) formData.append("force_reconvert", "true");

  const response = await fetch(`${BASE_URL}/jobs`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
  }

  return response.json();
}

export async function listJobs(): Promise<Job[]> {
  const response = await fetch(`${BASE_URL}/jobs`);
  if (!response.ok) throw new Error("Failed to fetch jobs");
  return response.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const response = await fetch(`${BASE_URL}/jobs/${jobId}`);
  if (!response.ok) throw new Error(`Failed to fetch job ${jobId}`);
  return response.json();
}

export async function getJobResult(jobId: string): Promise<JobResult> {
  const response = await fetch(`${BASE_URL}/jobs/${jobId}/result`);
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch job result");
  }
  return response.json();
}

export async function cancelJob(jobId: string): Promise<{ job_id: string; status: string }> {
  const response = await fetch(`${BASE_URL}/jobs/${jobId}/cancel`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to cancel job");
  return response.json();
}

export async function getSystemStatus(): Promise<SystemStatus> {
  const response = await fetch(`${BASE_URL}/system/status`);
  if (!response.ok) throw new Error("Failed to fetch system status");
  return response.json();
}

export function getDownloadUrl(jobId: string, format: "md" | "zip" = "zip"): string {
  return `${BASE_URL}/jobs/${jobId}/download?format=${format}`;
}

export function getPdfUrl(jobId: string): string {
  return `${BASE_URL}/jobs/${jobId}/file`;
}

export function getAssetUrl(jobId: string, assetFilename: string): string {
  // Strip any 'assets/' prefix from the filename
  const cleanName = assetFilename.replace(/^assets\//, "");
  return `${BASE_URL}/jobs/${jobId}/assets/${cleanName}`;
}
