import React, { useEffect, useRef, useState, useCallback } from "react";
import * as pdfjsLib from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.mjs?url";
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Loader2,
  AlertCircle,
} from "lucide-react";

// Configure worker
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

interface PDFViewerProps {
  url: string;
  initialPage?: number;
  onPageChange?: (page: number, total: number) => void;
}

export const PDFViewer: React.FC<PDFViewerProps> = ({
  url,
  initialPage = 1,
  onPageChange,
}) => {
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [totalPages, setTotalPages] = useState<number>(0);
  const [scale, setScale] = useState<number>(1.2);
  const [loading, setLoading] = useState<boolean>(true);
  const [rendering, setRendering] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const renderTaskRef = useRef<any>(null);

  // Load document
  useEffect(() => {
    let isCancelled = false;
    let loadingTask: any = null;
    setLoading(true);
    setError(null);

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load PDF: HTTP ${res.status}`);
        return res.arrayBuffer();
      })
      .then((data) => {
        if (isCancelled) return null;
        loadingTask = pdfjsLib.getDocument({
          data,
          cMapUrl: "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.4.168/cmaps/",
          cMapPacked: true,
        });
        return loadingTask.promise;
      })
      .then((doc) => {
        if (!isCancelled && doc) {
          setPdfDoc(doc);
          setTotalPages(doc.numPages);
          setCurrentPage(1);
          setLoading(false);
          if (onPageChange) {
            onPageChange(1, doc.numPages);
          }
        }
      })
      .catch((err) => {
        if (!isCancelled) {
          console.error("Error loading PDF:", err);
          setError("Failed to load PDF file.");
          setLoading(false);
        }
      });

    return () => {
      isCancelled = true;
      if (loadingTask) {
        loadingTask.destroy();
      }
    };
  }, [url]);

  // Render current page
  const renderPage = useCallback(
    async (pageNum: number) => {
      if (!pdfDoc || !canvasRef.current) return;

      if (renderTaskRef.current) {
        try {
          renderTaskRef.current.cancel();
        } catch {
          // ignore cancel error
        }
      }

      setRendering(true);

      try {
        const page = await pdfDoc.getPage(pageNum);
        const viewport = page.getViewport({ scale });
        const canvas = canvasRef.current;
        if (!canvas) return;

        const context = canvas.getContext("2d");
        if (!context) return;

        canvas.height = viewport.height;
        canvas.width = viewport.width;

        const renderContext = {
          canvasContext: context,
          viewport: viewport,
        };

        const task = page.render(renderContext);
        renderTaskRef.current = task;
        await task.promise;
      } catch (err: any) {
        if (err?.name !== "RenderingCancelledException") {
          console.error("Render error:", err);
        }
      } finally {
        setRendering(false);
      }
    },
    [pdfDoc, scale]
  );

  useEffect(() => {
    if (pdfDoc && currentPage > 0) {
      renderPage(currentPage);
    }
  }, [pdfDoc, currentPage, scale, renderPage]);

  const handlePrevPage = () => {
    if (currentPage > 1) {
      const next = currentPage - 1;
      setCurrentPage(next);
      onPageChange?.(next, totalPages);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      const next = currentPage + 1;
      setCurrentPage(next);
      onPageChange?.(next, totalPages);
    }
  };

  const handleZoomIn = () => setScale((s) => Math.min(s + 0.2, 3.0));
  const handleZoomOut = () => setScale((s) => Math.max(s - 0.2, 0.5));
  const handleResetZoom = () => setScale(1.2);

  return (
    <div className="flex flex-col h-full bg-slate-950 border-r border-slate-800">
      {/* PDF Controls Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800 text-xs">
        <div className="flex items-center gap-1.5 text-slate-300">
          <button
            onClick={handlePrevPage}
            disabled={currentPage <= 1 || loading}
            className="p-1 hover:bg-slate-800 rounded disabled:opacity-40 disabled:hover:bg-transparent text-slate-300"
            title="Previous Page"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="font-mono text-xs px-1">
            Page {currentPage} of {totalPages || "-"}
          </span>
          <button
            onClick={handleNextPage}
            disabled={currentPage >= totalPages || loading}
            className="p-1 hover:bg-slate-800 rounded disabled:opacity-40 disabled:hover:bg-transparent text-slate-300"
            title="Next Page"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-1 text-slate-300">
          <button
            onClick={handleZoomOut}
            className="p-1 hover:bg-slate-800 rounded text-slate-300"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="font-mono text-xs w-12 text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            className="p-1 hover:bg-slate-800 rounded text-slate-300"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleResetZoom}
            className="p-1 hover:bg-slate-800 rounded text-slate-300 ml-1"
            title="Fit / Reset Zoom"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* PDF Canvas Container */}
      <div className="flex-1 overflow-auto flex items-center justify-center p-4 bg-slate-950/80 custom-scrollbar">
        {loading && (
          <div className="flex flex-col items-center gap-2 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
            <p className="text-xs">Loading PDF document...</p>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-300 text-xs">
            <AlertCircle className="w-4 h-4 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {!loading && !error && (
          <div className="relative shadow-2xl rounded border border-slate-800 bg-white">
            <canvas ref={canvasRef} className="block max-w-full h-auto" />
            {rendering && (
              <div className="absolute top-2 right-2 p-1.5 bg-slate-900/80 rounded-full text-indigo-400 shadow">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
