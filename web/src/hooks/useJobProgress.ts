import { useEffect, useState } from "react";
import { JobStatus } from "../types";

export interface JobProgressState {
  jobId: string;
  status: JobStatus;
  currentPage: number;
  totalPages: number;
  engineUsed: string;
  error?: string;
  isFinished: boolean;
}

export function useJobProgress(
  jobId: string | null,
  onComplete?: () => void
): JobProgressState | null {
  const [progress, setProgress] = useState<JobProgressState | null>(null);

  useEffect(() => {
    if (!jobId) {
      setProgress(null);
      return;
    }

    const eventSource = new EventSource(`/api/jobs/${jobId}/events`);

    const handleEvent = (event: MessageEvent, defaultStatus?: JobStatus) => {
      try {
        const data = JSON.parse(event.data);
        const status: JobStatus = (data.status as JobStatus) || defaultStatus || "processing";
        const isFinished = ["completed", "failed", "cancelled"].includes(status);

        setProgress({
          jobId,
          status,
          currentPage: data.current_page || 0,
          totalPages: data.total_pages || 0,
          engineUsed: data.engine_used || data.engines_used?.[0] || "",
          error: data.error,
          isFinished,
        });

        if (isFinished) {
          eventSource.close();
          if (status === "completed" && onComplete) {
            onComplete();
          }
        }
      } catch (err) {
        console.error("Failed to parse SSE event:", err);
      }
    };

    eventSource.addEventListener("state", (e) => handleEvent(e));
    eventSource.addEventListener("progress", (e) => handleEvent(e, "processing"));
    eventSource.addEventListener("complete", (e) => handleEvent(e, "completed"));
    eventSource.addEventListener("cancelled", (e) => handleEvent(e, "cancelled"));
    eventSource.addEventListener("error", (e) => {
      if ((e as MessageEvent).data) {
        handleEvent(e as MessageEvent, "failed");
      } else {
        // Network or disconnect error
        eventSource.close();
      }
    });

    return () => {
      eventSource.close();
    };
  }, [jobId, onComplete]);

  return progress;
}
