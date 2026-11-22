import React, { useState } from "react";
import { Job, JobResult } from "../types";
import { PDFViewer } from "./PDFViewer";
import { MarkdownViewer } from "./MarkdownViewer";
import { MarkdownEditor } from "./MarkdownEditor";
import { ExportToolbar, ViewMode } from "./ExportToolbar";
import { getPdfUrl } from "../api";
import { FileText, Loader2, AlertTriangle } from "lucide-react";

interface SplitPaneViewerProps {
  job: Job | null;
  result: JobResult | null;
  loadingResult: boolean;
}

export const SplitPaneViewer: React.FC<SplitPaneViewerProps> = ({
  job,
  result,
  loadingResult,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>("preview");
  const [editedMarkdown, setEditedMarkdown] = useState<string>("");

  // Update local editedMarkdown when a new result comes in
  React.useEffect(() => {
    if (result?.markdown) {
      setEditedMarkdown(result.markdown);
    }
  }, [result?.markdown]);

  if (!job) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500 bg-slate-950">
        <FileText className="w-16 h-16 mb-4 stroke-[1] text-slate-700" />
        <h3 className="text-base font-medium text-slate-300">No Document Selected</h3>
        <p className="text-xs text-slate-500 max-w-sm mt-1">
          Select a conversion task from the sidebar or upload a new PDF to inspect side-by-side.
        </p>
      </div>
    );
  }

  // If job is in progress or pending
  if (job.status === "processing" || job.status === "pending") {
    const progressPercent =
      job.total_pages > 0 ? Math.round((job.current_page / job.total_pages) * 100) : 0;

    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400 bg-slate-950">
        <div className="p-4 bg-indigo-600/10 rounded-2xl border border-indigo-500/20 mb-4">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-400" />
        </div>
        <h3 className="text-lg font-semibold text-slate-200">
          {job.status === "pending" ? "Waiting in Queue..." : "Converting Document..."}
        </h3>
        <p className="text-xs text-slate-400 mt-1 max-w-md">
          {job.filename} • {job.mode.toUpperCase()} Mode
        </p>

        {job.status === "processing" && (
          <div className="w-72 mt-6">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5 font-mono">
              <span>
                Page {job.current_page} / {job.total_pages || "?"}
              </span>
              <span>{progressPercent}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700/50">
              <div
                className="bg-indigo-500 h-2 rounded-full transition-all duration-300 shadow-sm shadow-indigo-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            {job.engine_used && (
              <p className="text-[11px] text-slate-500 mt-2 font-mono">
                Active Engine: <span className="text-slate-300">{job.engine_used}</span>
              </p>
            )}
          </div>
        )}
      </div>
    );
  }

  // If job failed
  if (job.status === "failed") {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-red-400 bg-slate-950">
        <div className="p-4 bg-red-900/20 rounded-2xl border border-red-800/30 mb-4">
          <AlertTriangle className="w-10 h-10 text-red-400" />
        </div>
        <h3 className="text-lg font-semibold text-red-200">Conversion Failed</h3>
        <p className="text-xs text-slate-400 mt-1">{job.filename}</p>
        <div className="mt-4 p-4 bg-slate-900 border border-red-900/40 rounded-xl text-left max-w-lg">
          <p className="text-xs font-mono text-red-300 break-words">
            {job.error_message || "An unexpected error occurred during processing."}
          </p>
        </div>
      </div>
    );
  }

  const pdfUrl = getPdfUrl(job.id);
  const markdownText = editedMarkdown || result?.markdown || "";
  const hasAssets = (result?.assets?.length ?? 0) > 0;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-slate-950">
      {/* Top Document Header */}
      <div className="px-6 py-2.5 bg-slate-900/60 border-b border-slate-800 flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-slate-200 truncate max-w-md" title={job.filename}>
            {job.filename}
          </span>
          <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700/60">
            {job.total_pages} pages
          </span>
          {job.engine_used && (
            <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-slate-800 text-emerald-300 border border-slate-700/60">
              {job.engine_used}
            </span>
          )}
        </div>

        {job.completed_at && (
          <div className="text-[11px] text-slate-500">
            Finished: {new Date(job.completed_at).toLocaleTimeString()}
          </div>
        )}
      </div>

      {/* Split Viewer: Left PDF / Right Markdown */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 overflow-hidden">
        {/* Left Pane: PDF Viewer */}
        <div className="h-full overflow-hidden border-b lg:border-b-0 lg:border-r border-slate-800">
          <PDFViewer url={pdfUrl} />
        </div>

        {/* Right Pane: Markdown Viewer / Editor */}
        <div className="h-full flex flex-col overflow-hidden bg-slate-950">
          <ExportToolbar
            jobId={job.id}
            markdown={markdownText}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            hasAssets={hasAssets}
          />

          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {loadingResult ? (
              <div className="flex items-center justify-center h-full text-slate-400 gap-2">
                <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
                <span className="text-xs">Loading Markdown...</span>
              </div>
            ) : viewMode === "preview" ? (
              <MarkdownViewer jobId={job.id} markdown={markdownText} />
            ) : (
              <MarkdownEditor value={markdownText} onChange={setEditedMarkdown} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
