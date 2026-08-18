import React, { useState, useRef, useCallback } from "react";
import { SlidersHorizontal, Columns, SplitSquareVertical } from "lucide-react";

interface BeforeAfterSliderProps {
  originalSrc: string;
  processedSrc: string;
  originalLabel?: string;
  processedLabel?: string;
  className?: string;
}

export const BeforeAfterSlider: React.FC<BeforeAfterSliderProps> = ({
  originalSrc,
  processedSrc,
  originalLabel = "Original",
  processedLabel = "Processed",
  className = "",
}) => {
  const [sliderPos, setSliderPos] = useState<number>(50); // percentage
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<"slider" | "side_by_side">("slider");
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMove = useCallback(
    (clientX: number) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = clientX - rect.left;
      const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
      setSliderPos(percentage);
    },
    []
  );

  const handleMouseDown = () => setIsDragging(true);
  const handleMouseUp = () => setIsDragging(false);

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) handleMove(e.clientX);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (e.touches.length > 0) handleMove(e.touches[0].clientX);
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Top View Mode Switcher */}
      <div className="flex items-center justify-between text-xs text-slate-400 px-1">
        <span className="font-medium text-slate-300">Live Preview & Comparison</span>
        <div className="flex items-center gap-1 bg-white/[0.04] p-1 rounded-lg border border-white/[0.08]">
          <button
            type="button"
            onClick={() => setViewMode("slider")}
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-all ${
              viewMode === "slider"
                ? "bg-sky-500 text-white font-semibold shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <SplitSquareVertical className="w-3.5 h-3.5" />
            <span>Split Slider</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode("side_by_side")}
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-all ${
              viewMode === "side_by_side"
                ? "bg-sky-500 text-white font-semibold shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Columns className="w-3.5 h-3.5" />
            <span>Side by Side</span>
          </button>
        </div>
      </div>

      {viewMode === "slider" ? (
        <div
          ref={containerRef}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onMouseMove={handleMouseMove}
          onTouchMove={handleTouchMove}
          className="relative w-full h-80 md:h-96 rounded-2xl overflow-hidden select-none cursor-ew-resize bg-black/40 border border-white/[0.08] shadow-2xl flex items-center justify-center"
        >
          {/* Base Layer: Processed Image */}
          <img
            src={processedSrc}
            alt={processedLabel}
            className="absolute inset-0 w-full h-full object-contain pointer-events-none"
          />

          {/* Top Layer (Clipped): Original Image */}
          <div
            className="absolute inset-0 overflow-hidden pointer-events-none"
            style={{ width: `${sliderPos}%` }}
          >
            <img
              src={originalSrc}
              alt={originalLabel}
              className="absolute inset-0 w-full h-full object-contain pointer-events-none"
              style={{
                width: containerRef.current ? `${containerRef.current.clientWidth}px` : "100%",
                maxWidth: "none",
              }}
            />
          </div>

          {/* Divider Line & Handle */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg pointer-events-none"
            style={{ left: `${sliderPos}%` }}
          >
            <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 rounded-full bg-white text-slate-900 shadow-xl flex items-center justify-center border-2 border-sky-500 ring-4 ring-sky-500/20">
              <SlidersHorizontal className="w-4 h-4 text-slate-800" />
            </div>
          </div>

          {/* Floating Badges */}
          <div className="absolute top-3 left-3 pointer-events-none">
            <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-black/70 text-slate-200 backdrop-blur-md border border-white/10 shadow">
              {originalLabel}
            </span>
          </div>
          <div className="absolute top-3 right-3 pointer-events-none">
            <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-sky-500/80 text-white backdrop-blur-md border border-sky-400/30 shadow">
              {processedLabel}
            </span>
          </div>
        </div>
      ) : (
        /* Side by side view */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="relative rounded-2xl bg-black/40 border border-white/[0.08] p-2 h-72 flex flex-col items-center justify-center">
            <span className="absolute top-3 left-3 px-2 py-0.5 rounded text-[11px] font-semibold bg-black/70 text-slate-300 border border-white/10">
              {originalLabel}
            </span>
            <img src={originalSrc} alt={originalLabel} className="max-h-full max-w-full object-contain rounded-lg" />
          </div>
          <div className="relative rounded-2xl bg-black/40 border border-sky-500/20 p-2 h-72 flex flex-col items-center justify-center">
            <span className="absolute top-3 left-3 px-2 py-0.5 rounded text-[11px] font-semibold bg-sky-500/80 text-white border border-sky-400/30">
              {processedLabel}
            </span>
            <img src={processedSrc} alt={processedLabel} className="max-h-full max-w-full object-contain rounded-lg" />
          </div>
        </div>
      )}
    </div>
  );
};
