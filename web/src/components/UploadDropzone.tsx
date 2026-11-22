import React, { useState, useRef, DragEvent } from "react";
import { UploadCloud, Settings, Lock, Sparkles, Loader2, AlertCircle } from "lucide-react";
import { ConversionMode } from "../types";
import { uploadJob } from "../api";

interface UploadDropzoneProps {
  onJobCreated: (jobId: string) => void;
}

export const UploadDropzone: React.FC<UploadDropzoneProps> = ({ onJobCreated }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [mode, setMode] = useState<ConversionMode>("auto");
  const [showOptions, setShowOptions] = useState(false);
  const [password, setPassword] = useState("");
  const [extractImages, setExtractImages] = useState(true);
  const [forceReconvert, setForceReconvert] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files).filter(
      (f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
    );

    if (files.length === 0) {
      setError("Please drop a valid PDF file.");
      return;
    }

    await processFiles(files);
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const files = Array.from(e.target.files);
    await processFiles(files);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const processFiles = async (files: File[]) => {
    setIsUploading(true);
    setError(null);

    try {
      for (const file of files) {
        const job = await uploadJob(file, {
          mode,
          password: password.trim() || undefined,
          extractImages,
          forceReconvert,
        });
        onJobCreated(job.id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload file";
      setError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
      {/* Drop Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all ${
          isDragging
            ? "border-indigo-500 bg-indigo-500/10 scale-[0.99]"
            : "border-slate-700 hover:border-slate-600 bg-slate-800/40 hover:bg-slate-800/60"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          multiple
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="flex flex-col items-center justify-center gap-2">
          <div className="p-3 bg-indigo-600/20 text-indigo-400 rounded-full">
            {isUploading ? (
              <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
            ) : (
              <UploadCloud className="w-6 h-6" />
            )}
          </div>
          <div>
            <p className="text-sm font-medium text-slate-200">
              {isUploading ? "Uploading and enqueuing..." : "Drop PDF files here or browse"}
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Supports standard, scanned, and mixed layout PDFs
            </p>
          </div>
        </div>
      </div>

      {/* Error notification */}
      {error && (
        <div className="mt-3 p-2.5 rounded-lg bg-red-900/40 border border-red-800/60 flex items-center gap-2 text-red-200 text-xs">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Mode Selector */}
      <div className="mt-3 pt-3 border-t border-slate-800/80">
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-medium text-slate-300">Conversion Mode</label>
          <button
            type="button"
            onClick={() => setShowOptions(!showOptions)}
            className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition-colors"
          >
            <Settings className="w-3.5 h-3.5" />
            <span>Options</span>
          </button>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {(
            [
              { id: "auto", label: "Auto (Smart)", desc: "Per-page routing" },
              { id: "fast", label: "Fast", desc: "Digital text" },
              { id: "deep", label: "Deep", desc: "Full OCR layout" },
            ] as const
          ).map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setMode(m.id)}
              className={`p-2 rounded-lg border text-left transition-all ${
                mode === m.id
                  ? "bg-indigo-600/20 border-indigo-500 text-white"
                  : "bg-slate-800/40 border-slate-700/60 text-slate-400 hover:text-slate-300 hover:bg-slate-800/80"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold">{m.label}</span>
                {m.id === "auto" && <Sparkles className="w-3 h-3 text-indigo-400" />}
              </div>
              <span className="text-[10px] text-slate-400 block mt-0.5">{m.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Advanced Collapsible Options */}
      {showOptions && (
        <div className="mt-3 pt-3 border-t border-slate-800/60 space-y-2 text-xs">
          <div>
            <label className="block text-slate-400 mb-1 flex items-center gap-1">
              <Lock className="w-3 h-3" /> PDF Password (optional)
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password if encrypted"
              className="w-full bg-slate-800/80 border border-slate-700 rounded px-2.5 py-1 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <label className="text-slate-300 flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={extractImages}
                onChange={(e) => setExtractImages(e.target.checked)}
                className="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0"
              />
              Extract & link images
            </label>

            <label className="text-slate-300 flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={forceReconvert}
                onChange={(e) => setForceReconvert(e.target.checked)}
                className="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0"
              />
              Bypass cache
            </label>
          </div>
        </div>
      )}
    </div>
  );
};
