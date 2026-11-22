import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { getAssetUrl } from "../api";

interface MarkdownViewerProps {
  jobId: string;
  markdown: string;
}

export const MarkdownViewer: React.FC<MarkdownViewerProps> = ({ jobId, markdown }) => {
  return (
    <div className="p-8 prose prose-invert max-w-none prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-800 prose-headings:text-slate-150 prose-a:text-indigo-400">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          img: ({ src, alt, ...props }) => {
            if (!src) return null;
            // Rewrite local asset references (e.g. assets/p0001_img00.png)
            const finalSrc = src.startsWith("assets/") || src.startsWith("./assets/")
              ? getAssetUrl(jobId, src.replace("./", ""))
              : src;

            return (
              <span className="block my-4">
                <img
                  src={finalSrc}
                  alt={alt || "Extracted image"}
                  className="rounded-lg border border-slate-700 shadow-md max-h-96 object-contain bg-slate-900/50"
                  loading="lazy"
                  {...props}
                />
                {alt && <span className="block text-xs text-slate-400 mt-1 italic">{alt}</span>}
              </span>
            );
          },
          table: ({ children, ...props }) => (
            <div className="overflow-x-auto my-4 border border-slate-800 rounded-lg">
              <table className="w-full text-left text-sm border-collapse" {...props}>
                {children}
              </table>
            </div>
          ),
          th: ({ children, ...props }) => (
            <th
              className="bg-slate-800/80 px-4 py-2 border-b border-slate-700 font-semibold text-slate-200"
              {...props}
            >
              {children}
            </th>
          ),
          td: ({ children, ...props }) => (
            <td className="px-4 py-2 border-b border-slate-800/60 text-slate-300" {...props}>
              {children}
            </td>
          ),
          code: ({ className, children, ...props }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code
                  className="bg-slate-800/80 text-indigo-300 px-1.5 py-0.5 rounded text-xs font-mono border border-slate-700/50"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
};
