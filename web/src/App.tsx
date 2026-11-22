import React, { useState, useEffect, useCallback } from "react";
import { Header } from "./components/Header";
import { UploadDropzone } from "./components/UploadDropzone";
import { JobList } from "./components/JobList";
import { SplitPaneViewer } from "./components/SplitPaneViewer";
import { useSystemStatus } from "./hooks/useSystemStatus";
import { useJobProgress } from "./hooks/useJobProgress";
import { Job, JobResult } from "./types";
import { listJobs, getJobResult } from "./api";

export const App: React.FC = () => {
  const { status: systemStatus, loading: statusLoading, refetch: refetchStatus } = useSystemStatus(8000);

  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [jobResult, setJobResult] = useState<JobResult | null>(null);
  const [loadingResult, setLoadingResult] = useState<boolean>(false);

  // Fetch list of jobs
  const fetchJobs = useCallback(async () => {
    try {
      const data = await listJobs();
      setJobs(data);
    } catch (err) {
      console.error("Failed to fetch jobs:", err);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // Selected job object
  const selectedJob = jobs.find((j) => j.id === selectedJobId) || null;

  // Fetch markdown result when selected job becomes completed
  const fetchResult = useCallback(async (jobId: string) => {
    setLoadingResult(true);
    try {
      const res = await getJobResult(jobId);
      setJobResult(res);
    } catch (err) {
      console.error("Failed to load result for job:", jobId, err);
      setJobResult(null);
    } finally {
      setLoadingResult(false);
    }
  }, []);

  useEffect(() => {
    if (selectedJob && selectedJob.status === "completed") {
      fetchResult(selectedJob.id);
    } else {
      setJobResult(null);
    }
  }, [selectedJob?.id, selectedJob?.status, fetchResult]);

  // Listen to SSE progress for selected job
  const activeSseId =
    selectedJob && (selectedJob.status === "pending" || selectedJob.status === "processing")
      ? selectedJob.id
      : null;

  const progress = useJobProgress(activeSseId, () => {
    // When completed, refresh jobs and system status
    fetchJobs();
    refetchStatus();
  });

  // Merge SSE progress updates into local jobs list state
  useEffect(() => {
    if (progress && selectedJobId === progress.jobId) {
      setJobs((prevJobs) =>
        prevJobs.map((j) => {
          if (j.id === progress.jobId) {
            return {
              ...j,
              status: progress.status,
              current_page: progress.currentPage,
              total_pages: progress.totalPages || j.total_pages,
              engine_used: progress.engineUsed || j.engine_used,
              error_message: progress.error || j.error_message,
            };
          }
          return j;
        })
      );
    }
  }, [progress, selectedJobId]);

  const handleJobCreated = (newJobId: string) => {
    fetchJobs();
    setSelectedJobId(newJobId);
    refetchStatus();
  };

  const handleSelectJob = (job: Job) => {
    setSelectedJobId(job.id);
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">
      <Header
        status={systemStatus}
        loading={statusLoading}
        onRefresh={() => {
          refetchStatus();
          fetchJobs();
        }}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Upload Dropzone & Job List */}
        <div className="w-80 md:w-96 flex flex-col h-full bg-slate-900/50 border-r border-slate-800 p-4 gap-4 overflow-hidden flex-shrink-0">
          <UploadDropzone onJobCreated={handleJobCreated} />
          <div className="flex-1 overflow-hidden">
            <JobList
              jobs={jobs}
              selectedJobId={selectedJobId}
              onSelectJob={handleSelectJob}
              onRefreshJobs={fetchJobs}
            />
          </div>
        </div>

        {/* Main Content Area: Split Pane Viewer */}
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          <SplitPaneViewer
            job={selectedJob}
            result={jobResult}
            loadingResult={loadingResult}
          />
        </div>
      </div>
    </div>
  );
};

export default App;
