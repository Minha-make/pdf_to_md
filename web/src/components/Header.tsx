import React from "react";
import { SystemStatus } from "../types";
import { Cpu, Zap, Activity, RefreshCw } from "lucide-react";

interface HeaderProps {
  status: SystemStatus | null;
  loading: boolean;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({ status, loading, onRefresh }) => {
  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white px-6 py-3.5 flex items-center justify-between shadow-md">
      <div className="flex items-center gap-3">
        <div className="bg-indigo-600 p-2 rounded-lg text-white shadow-indigo-500/20 shadow-lg">
          <Zap className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-lg tracking-tight text-white">OmniPDF2MD</h1>
            <span className="bg-slate-800 text-indigo-400 text-xs px-2 py-0.5 rounded-full font-mono font-medium border border-indigo-500/30">
              v{status?.version || "0.1.0"}
            </span>
          </div>
          <p className="text-xs text-slate-400">Local-first PDF to Markdown Converter Studio</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Compute Device Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-800/80 border border-slate-700/60 text-xs">
          <Cpu className="w-4 h-4 text-emerald-400" />
          <span className="text-slate-400">Compute:</span>
          <span className="font-medium text-emerald-300">
            {status?.compute?.device === "cuda" ? "GPU (CUDA)" : "CPU"}
          </span>
        </div>

        {/* Ollama Status Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-800/80 border border-slate-700/60 text-xs">
          <Activity
            className={`w-4 h-4 ${
              status?.services?.ollama_online ? "text-emerald-400" : "text-amber-400"
            }`}
          />
          <span className="text-slate-400">Ollama VLM:</span>
          <span
            className={`font-medium ${
              status?.services?.ollama_online ? "text-emerald-300" : "text-amber-300"
            }`}
          >
            {status?.services?.ollama_online ? "Online" : "Offline"}
          </span>
        </div>

        {/* Queue Status Badge */}
        {status?.queue && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-800/80 border border-slate-700/60 text-xs">
            <span className="text-slate-400">Queue:</span>
            <span className="font-semibold text-indigo-300">
              {status.queue.pending_count} pending
            </span>
          </div>
        )}

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={loading}
          className="p-1.5 hover:bg-slate-800 text-slate-400 hover:text-white rounded-md transition-colors"
          title="Refresh status"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-indigo-400" : ""}`} />
        </button>
      </div>
    </header>
  );
};
