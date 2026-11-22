import React from "react";

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
}

export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
  readOnly = false,
}) => {
  const lineCount = value ? value.split("\n").length : 0;
  const wordCount = value ? value.trim().split(/\s+/).filter(Boolean).length : 0;
  const charCount = value ? value.length : 0;

  return (
    <div className="flex flex-col h-full bg-slate-950 font-mono text-xs">
      <div className="flex-1 relative overflow-hidden">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          readOnly={readOnly}
          spellCheck={false}
          className="w-full h-full p-6 bg-slate-950 text-slate-200 resize-none focus:outline-none custom-scrollbar leading-relaxed selection:bg-indigo-600/30 font-mono text-[13px]"
          placeholder="Markdown output will appear here..."
        />
      </div>

      {/* Editor Status Bar */}
      <div className="px-6 py-2 bg-slate-900 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span>{lineCount} lines</span>
          <span>{wordCount} words</span>
          <span>{charCount} characters</span>
        </div>
        <div className="text-slate-500 font-mono">
          {readOnly ? "Read-Only" : "Editable"} • UTF-8
        </div>
      </div>
    </div>
  );
};
