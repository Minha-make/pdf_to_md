import React from "react";
import { Job, JobStatus } from "../types";
import {
  FileText,
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  StopCircle,
} from "lucide-react";
import { cancelJob } from "../api";

interface JobListProps {
  jobs: Job[];
  selectedJobId: string | null;
  onSelectJob: (job: Job) => void;
  onRefreshJobs: () => void;
}

export const JobList: React.FC<JobListProps> = ({
  jobs,
  selectedJobId,
  onSelectJob,
  onRefreshJobs,
}) => {
  const handleCancel = async (e: React.MouseEvent, jobId: string) => {
    e.stopPropagation();
    try {
      await cancelJob(jobId);
      onRefreshJobs();
    } catch (err) {
      console.error("Failed to cancel job:", err);
    }
  };

  const getStatusIcon = (status: JobStatus) => {
    switch (status) {
      case "pending":
        return <Clock className="w-3.5 h-3.5 text-amber-400" />;
      case "processing":
        return <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />;
      case "completed":
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case "failed":
        return <AlertTriangle className="w-3.5 h-3.5 text-red-400" />;
      case "cancelled":
        return <XCircle className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  const getStatusBadge = (status: JobStatus) => {
    const base = "text-[10px] px-2 py-0.5 rounded-full font-medium inline-flex items-center gap-1";
    switch (status) {
      case "pending":
        return <span className={`${base} bg-amber-500/10 text-amber-300 border border-amber-500/20`}>Pending</span>;
      case "processing":
        return <span className={`${base} bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 animate-pulse`}>Processing</span>;
      case "completed":
        return <span className={`${base} bg-emerald-500/10 text-emerald-300 border border-emerald-500/20`}>Done</span>;
      case "failed":
        return <span className={`${base} bg-red-500/10 text-red-300 border border-red-500/20`}>Failed</span>;
      case "cancelled":
        return <span className={`${base} bg-slate-500/10 text-slate-400 border border-slate-500/20`}>Cancelled</span>;
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-1 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
        <span>Conversion Tasks ({jobs.length})</span>
      </div>

      {jobs.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-slate-500">
          <FileText className="w-8 h-8 mb-2 stroke-[1.5] text-slate-600" />
          <p className="text-xs">No conversions yet</p>
          <p className="text-[11px] text-slate-600 mt-1">Upload a PDF above to begin</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
          {jobs.map((job) => {
            const isSelected = job.id === selectedJobId;
            const isCancellable = job.status === "pending" || job.status === "processing";
            const progressPercent =
              job.total_pages > 0 ? Math.round((job.current_page / job.total_pages) * 100) : 0;

            return (
              <div
                key={job.id}
                onClick={() => onSelectJob(job)}
                className={`group p-3 rounded-xl border text-left cursor-pointer transition-all relative ${
                  isSelected
                    ? "bg-slate-800/90 border-indigo-500 shadow-md"
                    : "bg-slate-900/60 hover:bg-slate-800/50 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    {getStatusIcon(job.status)}
                    <span
                      className="text-xs font-medium text-slate-200 truncate"
                      title={job.filename}
                    >
                      {job.filename}
                    </span>
                  </div>

                  <div className="flex items-center gap-1">
                    {getStatusBadge(job.status)}
                    {isCancellable && (
                      <button
                        onClick={(e) => handleCancel(e, job.id)}
                        className="p-1 text-slate-500 hover:text-red-400 rounded transition-colors"
                        title="Cancel job"
                      >
                        <StopCircle className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Progress bar for running or completed jobs */}
                {job.status === "processing" && (
                  <div className="mt-2.5">
                    <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                      <span>
                        Page {job.current_page} of {job.total_pages || "?"}
                      </span>
                      <span>{progressPercent}%</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-indigo-500 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${progressPercent}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Metadata tags */}
                <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500">
                  <span className="capitalize">{job.mode} Mode</span>
                  {job.engine_used && (
                    <span className="font-mono bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">
                      {job.engine_used}
                    </span>
                  )}
                  {job.cached && (
                    <span className="text-emerald-400 font-mono text-[9px]">CACHED</span>
                  )}
                </div>

                {job.error_message && (
                  <p className="mt-1.5 text-[10px] text-red-400 truncate" title={job.error_message}>
                    {job.error_message}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
