import React, { useState } from "react";
import { Eye, Code, Copy, Check, Download, Archive } from "lucide-react";
import { getDownloadUrl } from "../api";

export type ViewMode = "preview" | "raw";

interface ExportToolbarProps {
  jobId: string;
  markdown: string;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  hasAssets?: boolean;
}

export const ExportToolbar: React.FC<ExportToolbarProps> = ({
  jobId,
  markdown,
  viewMode,
  onViewModeChange,
  hasAssets = false,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy markdown:", err);
    }
  };

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800 text-xs">
      {/* View Switcher Tabs */}
      <div className="flex items-center bg-slate-950 p-0.5 rounded-lg border border-slate-800">
        <button
          onClick={() => onViewModeChange("preview")}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
            viewMode === "preview"
              ? "bg-indigo-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Eye className="w-3.5 h-3.5" />
          <span>Rendered</span>
        </button>
        <button
          onClick={() => onViewModeChange("raw")}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
            viewMode === "raw"
              ? "bg-indigo-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Code className="w-3.5 h-3.5" />
          <span>Raw Markdown</span>
        </button>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-2">
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700/60"
          title="Copy markdown content to clipboard"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-medium">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>

        <a
          href={getDownloadUrl(jobId, "md")}
          download
          className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700/60"
          title="Download single Markdown (.md) file"
        >
          <Download className="w-3.5 h-3.5" />
          <span>.MD</span>
        </a>

        {hasAssets && (
          <a
            href={getDownloadUrl(jobId, "zip")}
            download
            className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 hover:text-indigo-200 transition-colors border border-indigo-500/30 font-medium"
            title="Download ZIP archive containing Markdown and extracted image assets"
          >
            <Archive className="w-3.5 h-3.5" />
            <span>ZIP (Assets)</span>
          </a>
        )}
      </div>
    </div>
  );
};
