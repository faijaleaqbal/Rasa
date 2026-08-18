import React, { useState, useEffect, useRef } from "react";
import {
  Minimize2,
  Maximize2,
  Crop as CropIcon,
  RefreshCw,
  Sparkles,
  Sliders,
  FileImage,
  Download,
  Upload,
  Layers,
  Info,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  RotateCcw,
  FlipHorizontal,
  FlipVertical,
  Type,
  Eye,
  FileArchive,
  ArrowRight,
  Printer,
  ShieldAlert,
  SlidersHorizontal,
  Trash2,
  X,
} from "lucide-react";

import {
  ToolTab,
  PresetItem,
  PipelineOptions,
  ProcessResponse,
  BatchResponse,
  ImageMetadataResponse,
} from "./types";
import { BeforeAfterSlider } from "./BeforeAfterSlider";

const TARGET_SIZE_PRESETS = [
  { label: "5 KB", value: 5 },
  { label: "10 KB", value: 10 },
  { label: "20 KB (Govt Sign)", value: 20 },
  { label: "50 KB (Govt Photo)", value: 50 },
  { label: "100 KB", value: 100 },
  { label: "200 KB", value: 200 },
  { label: "500 KB", value: 500 },
  { label: "1 MB", value: 1024 },
  { label: "2 MB", value: 2048 },
];

const ASPECT_RATIO_PRESETS = [
  { label: "Free", value: "" },
  { label: "1:1 (Square)", value: "1:1" },
  { label: "4:3 (Standard)", value: "4:3" },
  { label: "3:4 (Portrait)", value: "3:4" },
  { label: "16:9 (Widescreen)", value: "16:9" },
  { label: "9:16 (Story/Reel)", value: "9:16" },
  { label: "2:3 (Photo 4x6)", value: "2:3" },
  { label: "3:2 (Landscape)", value: "3:2" },
];

export const ImageToolsStudio: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ToolTab>("compress");
  const [file, setFile] = useState<File | null>(null);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [batchFiles, setBatchFiles] = useState<File[]>([]);
  const [presets, setPresets] = useState<PresetItem[]>([]);
  const [presetCategory, setPresetCategory] = useState<string>("All");

  // Options State
  const [options, setOptions] = useState<PipelineOptions>({
    unit: "px",
    maintain_aspect: true,
    resample_filter: "lanczos",
    scale_mode: "fit",
    crop_shape: "rect",
    rotation_angle: 0,
    flip_horizontal: false,
    flip_vertical: false,
    matte_color: "#FFFFFF",
    auto_contrast: false,
    brightness: 1.0,
    contrast: 1.0,
    sharpness: 1.0,
    color_balance: 1.0,
    denoise: false,
    upscale_factor: 1.0,
    watermark_opacity: 0.6,
    watermark_position: "bottom-right",
    privacy_effect: "blur",
    strip_metadata: true,
  });

  // Compression specific state
  const [compressMode, setCompressMode] = useState<"target" | "quality">("target");
  const [customTargetKb, setCustomTargetKb] = useState<string>("50");
  const [qualitySlider, setQualitySlider] = useState<number>(85);

  // Processing & Results State
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processResult, setProcessResult] = useState<ProcessResponse | null>(null);
  const [batchResult, setBatchResult] = useState<BatchResponse | null>(null);
  const [metadataInfo, setMetadataInfo] = useState<ImageMetadataResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const batchInputRef = useRef<HTMLInputElement>(null);

  // Load Presets on Mount
  useEffect(() => {
    fetch("/api/image/presets")
      .then((res) => res.json())
      .then((data) => {
        if (data.presets) setPresets(data.presets);
      })
      .catch(() => {
        // Fallback default presets if offline
      });
  }, []);

  // Handle Single File Selection
  const handleFileChange = (selectedFile: File) => {
    setFile(selectedFile);
    setProcessResult(null);
    setErrorMessage(null);
    setMetadataInfo(null);

    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewSrc(objectUrl);

    // Fetch initial metadata
    const form = new FormData();
    form.append("file", selectedFile);
    fetch("/api/image/metadata", { method: "POST", body: form })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setMetadataInfo(data);
          // Set initial resize dimensions
          setOptions((prev) => ({
            ...prev,
            target_width: data.basic.width,
            target_height: data.basic.height,
            dpi: data.basic.dpi_x || 300,
          }));
        }
      })
      .catch(() => {});
  };

  // Handle Drag & Drop
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (activeTab === "batch") {
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        setBatchFiles(Array.from(e.dataTransfer.files));
        setBatchResult(null);
      }
    } else {
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFileChange(e.dataTransfer.files[0]);
      }
    }
  };

  // Process Single Image Pipeline
  const handleProcessImage = async () => {
    if (!file) {
      setErrorMessage("Please select or drop an image file first.");
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);

    try {
      const form = new FormData();
      form.append("file", file);

      const requestOptions: any = { ...options };

      if (activeTab === "compress") {
        if (compressMode === "target") {
          requestOptions.target_size_kb = parseFloat(customTargetKb) || 50;
          delete requestOptions.quality;
        } else {
          requestOptions.quality = qualitySlider;
          delete requestOptions.target_size_kb;
        }
      }

      form.append("options", JSON.stringify(requestOptions));

      const res = await fetch("/api/image/process", {
        method: "POST",
        body: form,
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || "Failed to process image.");
      }

      setProcessResult(data);
    } catch (err: any) {
      setErrorMessage(err.message || "An unexpected error occurred during processing.");
    } finally {
      setIsProcessing(false);
    }
  };

  // Process Bulk Batch Pipeline
  const handleProcessBatch = async () => {
    if (batchFiles.length === 0) {
      setErrorMessage("Please select multiple files for batch processing.");
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);

    try {
      const form = new FormData();
      batchFiles.forEach((f) => form.append("files", f));

      const requestOptions: any = { ...options };
      if (activeTab === "compress") {
        if (compressMode === "target") {
          requestOptions.target_size_kb = parseFloat(customTargetKb) || 50;
        } else {
          requestOptions.quality = qualitySlider;
        }
      }

      form.append("options", JSON.stringify(requestOptions));

      const res = await fetch("/api/image/batch", {
        method: "POST",
        body: form,
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || "Failed to process batch files.");
      }

      setBatchResult(data);
    } catch (err: any) {
      setErrorMessage(err.message || "Batch processing failed.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApplyPreset = (preset: PresetItem) => {
    setOptions((prev) => ({
      ...prev,
      preset_id: preset.id,
      target_width: preset.width,
      target_height: preset.height,
      unit: (preset.unit as any) || "px",
      dpi: preset.dpi,
      output_format: (preset.format as any) || "JPEG",
      target_size_kb: preset.max_size_kb,
      crop_aspect_ratio: preset.aspect_ratio,
    }));
    setActiveTab("compress");
    if (preset.max_size_kb) {
      setCompressMode("target");
      setCustomTargetKb(preset.max_size_kb.toString());
    }
  };

  const resetAll = () => {
    setFile(null);
    setPreviewSrc(null);
    setBatchFiles([]);
    setProcessResult(null);
    setBatchResult(null);
    setMetadataInfo(null);
    setErrorMessage(null);
    setOptions({
      unit: "px",
      maintain_aspect: true,
      resample_filter: "lanczos",
      scale_mode: "fit",
      crop_shape: "rect",
      rotation_angle: 0,
      flip_horizontal: false,
      flip_vertical: false,
      matte_color: "#FFFFFF",
      auto_contrast: false,
      brightness: 1.0,
      contrast: 1.0,
      sharpness: 1.0,
      color_balance: 1.0,
      denoise: false,
      upscale_factor: 1.0,
      watermark_opacity: 0.6,
      watermark_position: "bottom-right",
      privacy_effect: "blur",
      strip_metadata: true,
    });
  };

  const presetCategories = ["All", "Passport & Visa", "Documents", "Govt & Exam Portals", "Social Media"];

  const filteredPresets =
    presetCategory === "All"
      ? presets
      : presets.filter((p) => p.category.toLowerCase().includes(presetCategory.toLowerCase().split(" ")[0]));

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6 pb-20">
      {/* Studio Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900/90 via-[#12141c]/90 to-slate-900/90 p-5 rounded-3xl border border-white/[0.08] shadow-2xl backdrop-blur-xl">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-sky-500 via-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <Sliders className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white tracking-tight">Alya Image Tools Studio</h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Production Engine
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Zero-loss compression, DPI calibration, biometric passport formats, bulk batch processing & privacy guard.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto">
          {(file || batchFiles.length > 0) && (
            <button
              onClick={resetAll}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs font-medium text-slate-300 border border-white/[0.08] transition-all"
            >
              <Trash2 className="w-3.5 h-3.5 text-rose-400" />
              <span>Reset</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Tool Tabs Navigation */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar bg-black/40 p-1.5 rounded-2xl border border-white/[0.06]">
        {[
          { id: "compress", label: "Compressor", icon: Minimize2 },
          { id: "resize", label: "Resizer", icon: Maximize2 },
          { id: "crop", label: "Crop & Rotate", icon: CropIcon },
          { id: "convert", label: "Converter", icon: RefreshCw },
          { id: "presets", label: "Presets", icon: Layers },
          { id: "dpi", label: "DPI & Print", icon: Printer },
          { id: "metadata", label: "EXIF & Info", icon: Info },
          { id: "enhance", label: "Enhance", icon: Sparkles },
          { id: "watermark", label: "Watermark & Blur", icon: Type },
          { id: "batch", label: "Bulk Batch", icon: FileArchive },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as ToolTab)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? "bg-gradient-to-r from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="flex items-start gap-3 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
          <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold text-rose-200">Operation Notice: </span>
            {errorMessage}
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-rose-200">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Grid: Upload & Controls on Left/Top, Live Preview & Results on Right/Bottom */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Controls (5 cols on lg) */}
        <div className="lg:col-span-5 space-y-5">
          {/* Upload Dropzone */}
          {activeTab !== "batch" ? (
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative border-2 border-dashed rounded-3xl p-6 text-center cursor-pointer transition-all ${
                file
                  ? "border-sky-500/40 bg-sky-500/[0.02]"
                  : "border-white/10 hover:border-sky-500/40 bg-white/[0.02] hover:bg-white/[0.04]"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif,image/bmp,image/tiff,image/heic,image/heif"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFileChange(e.target.files[0])}
              />
              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                  <Upload className="w-6 h-6" />
                </div>
                {file ? (
                  <div>
                    <p className="text-sm font-semibold text-white truncate max-w-xs">{file.name}</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      {(file.size / 1024).toFixed(1)} KB • Click or drag to change
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-semibold text-slate-200">Drag & drop image here or browse</p>
                    <p className="text-[11px] text-slate-400 mt-1">Supports JPG, PNG, WebP, HEIC, BMP, TIFF (up to 50 MB)</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* Bulk Batch Dropzone */
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => batchInputRef.current?.click()}
              className="border-2 border-dashed border-sky-500/30 rounded-3xl p-6 text-center cursor-pointer bg-sky-500/[0.02] hover:bg-sky-500/[0.05] transition-all"
            >
              <input
                ref={batchInputRef}
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp,image/gif,image/bmp,image/tiff,image/heic"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    setBatchFiles(Array.from(e.target.files));
                    setBatchResult(null);
                  }
                }}
              />
              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <FileArchive className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-200">
                    {batchFiles.length > 0 ? `${batchFiles.length} files selected` : "Select multiple images for bulk processing"}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-1">Upload multiple photos and download as individual files or ZIP</p>
                </div>
              </div>
            </div>
          )}

          {/* Tab Specific Controls Panel */}
          <div className="rounded-3xl bg-slate-900/60 border border-white/[0.08] p-5 space-y-4 backdrop-blur-xl">
            {/* 1. COMPRESSOR TAB */}
            {activeTab === "compress" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-300">Compression Mode</label>
                  <div className="flex items-center gap-1 bg-black/40 p-1 rounded-xl border border-white/[0.06]">
                    <button
                      type="button"
                      onClick={() => setCompressMode("target")}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                        compressMode === "target" ? "bg-sky-500 text-white font-semibold shadow" : "text-slate-400"
                      }`}
                    >
                      Target File Size
                    </button>
                    <button
                      type="button"
                      onClick={() => setCompressMode("quality")}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                        compressMode === "quality" ? "bg-sky-500 text-white font-semibold shadow" : "text-slate-400"
                      }`}
                    >
                      Quality %
                    </button>
                  </div>
                </div>

                {compressMode === "target" ? (
                  <div className="space-y-3">
                    <label className="text-xs text-slate-400">Quick Target Limits</label>
                    <div className="grid grid-cols-3 gap-2">
                      {TARGET_SIZE_PRESETS.map((p) => (
                        <button
                          key={p.label}
                          type="button"
                          onClick={() => setCustomTargetKb(p.value.toString())}
                          className={`px-2.5 py-2 rounded-xl text-xs font-medium border transition-all truncate ${
                            customTargetKb === p.value.toString()
                              ? "bg-sky-500/20 border-sky-500 text-sky-300 font-semibold"
                              : "bg-white/[0.02] border-white/[0.06] text-slate-300 hover:bg-white/[0.06]"
                          }`}
                        >
                          {p.label}
                        </button>
                      ))}
                    </div>

                    <div className="pt-2">
                      <label className="text-xs text-slate-400">Custom Target (KB)</label>
                      <div className="relative mt-1">
                        <input
                          type="number"
                          min="1"
                          max="20480"
                          value={customTargetKb}
                          onChange={(e) => setCustomTargetKb(e.target.value)}
                          className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
                          placeholder="e.g. 50"
                        />
                        <span className="absolute right-3 top-2.5 text-xs text-slate-400">KB</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">Encoding Quality</span>
                      <span className="font-semibold text-sky-400">{qualitySlider}%</span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="100"
                      value={qualitySlider}
                      onChange={(e) => setQualitySlider(parseInt(e.target.value))}
                      className="w-full accent-sky-500 cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-slate-500">
                      <span>Max Compression (1%)</span>
                      <span>Balanced (80%)</span>
                      <span>Max Quality (100%)</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 2. RESIZER TAB */}
            {activeTab === "resize" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-300">Dimension Units</label>
                  <div className="flex items-center gap-1 bg-black/40 p-1 rounded-xl border border-white/[0.06]">
                    {(["px", "cm", "mm", "in"] as const).map((u) => (
                      <button
                        key={u}
                        type="button"
                        onClick={() => setOptions((prev) => ({ ...prev, unit: u }))}
                        className={`px-2.5 py-1 rounded-lg text-xs font-medium uppercase transition-all ${
                          options.unit === u ? "bg-sky-500 text-white font-semibold shadow" : "text-slate-400"
                        }`}
                      >
                        {u}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400">Width ({options.unit})</label>
                    <input
                      type="number"
                      step="any"
                      value={options.target_width || ""}
                      onChange={(e) =>
                        setOptions((prev) => ({
                          ...prev,
                          target_width: parseFloat(e.target.value) || undefined,
                        }))
                      }
                      className="mt-1 w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
                      placeholder="Auto"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400">Height ({options.unit})</label>
                    <input
                      type="number"
                      step="any"
                      value={options.target_height || ""}
                      onChange={(e) =>
                        setOptions((prev) => ({
                          ...prev,
                          target_height: parseFloat(e.target.value) || undefined,
                        }))
                      }
                      className="mt-1 w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
                      placeholder="Auto"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={options.maintain_aspect}
                      onChange={(e) => setOptions((prev) => ({ ...prev, maintain_aspect: e.target.checked }))}
                      className="rounded bg-black/40 border-white/20 text-sky-500 focus:ring-0"
                    />
                    <span>Maintain Aspect Ratio</span>
                  </label>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div>
                    <label className="text-xs text-slate-400">Resampling Filter</label>
                    <select
                      value={options.resample_filter}
                      onChange={(e) => setOptions((prev) => ({ ...prev, resample_filter: e.target.value as any }))}
                      className="mt-1 w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                    >
                      <option value="lanczos">Lanczos (Sharpest)</option>
                      <option value="bicubic">Bicubic (Smooth)</option>
                      <option value="bilinear">Bilinear (Fast)</option>
                      <option value="nearest">Nearest Neighbor</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-slate-400">Scale Mode</label>
                    <select
                      value={options.scale_mode}
                      onChange={(e) => setOptions((prev) => ({ ...prev, scale_mode: e.target.value as any }))}
                      className="mt-1 w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                    >
                      <option value="fit">Fit / Contain</option>
                      <option value="cover">Cover & Crop</option>
                      <option value="stretch">Stretch Exact</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* 3. CROP & ROTATE TAB */}
            {activeTab === "crop" && (
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold text-slate-300">Preset Aspect Ratio</label>
                  <div className="grid grid-cols-4 gap-2 mt-2">
                    {ASPECT_RATIO_PRESETS.map((ar) => (
                      <button
                        key={ar.label}
                        type="button"
                        onClick={() =>
                          setOptions((prev) => ({
                            ...prev,
                            crop_aspect_ratio: ar.value || undefined,
                            crop_shape: "rect",
                          }))
                        }
                        className={`px-2 py-1.5 rounded-xl text-[11px] font-medium border transition-all truncate ${
                          (options.crop_aspect_ratio || "") === ar.value && options.crop_shape === "rect"
                            ? "bg-sky-500/20 border-sky-500 text-sky-300 font-semibold"
                            : "bg-white/[0.02] border-white/[0.06] text-slate-300 hover:bg-white/[0.06]"
                        }`}
                      >
                        {ar.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300">Geometric Shape Mask</label>
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    <button
                      type="button"
                      onClick={() => setOptions((prev) => ({ ...prev, crop_shape: "rect" }))}
                      className={`px-3 py-2 rounded-xl text-xs font-medium border transition-all ${
                        options.crop_shape === "rect"
                          ? "bg-sky-500/20 border-sky-500 text-sky-300 font-semibold"
                          : "bg-white/[0.02] border-white/[0.06] text-slate-300"
                      }`}
                    >
                      Rectangle / Normal
                    </button>
                    <button
                      type="button"
                      onClick={() => setOptions((prev) => ({ ...prev, crop_shape: "circle" }))}
                      className={`px-3 py-2 rounded-xl text-xs font-medium border transition-all ${
                        options.crop_shape === "circle"
                          ? "bg-sky-500/20 border-sky-500 text-sky-300 font-semibold"
                          : "bg-white/[0.02] border-white/[0.06] text-slate-300"
                      }`}
                    >
                      Circle Avatar (Alpha)
                    </button>
                  </div>
                </div>

                <div className="pt-2 border-t border-white/[0.06]">
                  <label className="text-xs font-semibold text-slate-300">Transform & Flip</label>
                  <div className="flex items-center gap-2 mt-2">
                    <button
                      type="button"
                      onClick={() =>
                        setOptions((prev) => ({
                          ...prev,
                          rotation_angle: (prev.rotation_angle - 90 + 360) % 360,
                        }))
                      }
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-white/[0.03] border border-white/[0.08] text-xs hover:bg-white/[0.08] text-slate-200"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>-90°</span>
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        setOptions((prev) => ({
                          ...prev,
                          rotation_angle: (prev.rotation_angle + 90) % 360,
                        }))
                      }
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-white/[0.03] border border-white/[0.08] text-xs hover:bg-white/[0.08] text-slate-200"
                    >
                      <RotateCw className="w-3.5 h-3.5" />
                      <span>+90°</span>
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        setOptions((prev) => ({
                          ...prev,
                          flip_horizontal: !prev.flip_horizontal,
                        }))
                      }
                      className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl border text-xs transition-all ${
                        options.flip_horizontal
                          ? "bg-sky-500/20 border-sky-500 text-sky-300"
                          : "bg-white/[0.03] border-white/[0.08] text-slate-200"
                      }`}
                    >
                      <FlipHorizontal className="w-3.5 h-3.5" />
                      <span>Flip H</span>
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        setOptions((prev) => ({
                          ...prev,
                          flip_vertical: !prev.flip_vertical,
                        }))
                      }
                      className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl border text-xs transition-all ${
                        options.flip_vertical
                          ? "bg-sky-500/20 border-sky-500 text-sky-300"
                          : "bg-white/[0.03] border-white/[0.08] text-slate-200"
                      }`}
                    >
                      <FlipVertical className="w-3.5 h-3.5" />
                      <span>Flip V</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* 4. CONVERTER TAB */}
            {activeTab === "convert" && (
              <div className="space-y-4">
                <label className="text-xs font-semibold text-slate-300">Target Output Format</label>
                <div className="grid grid-cols-3 gap-2">
                  {(["JPEG", "PNG", "WEBP"] as const).map((fmt) => (
                    <button
                      key={fmt}
                      type="button"
                      onClick={() => setOptions((prev) => ({ ...prev, output_format: fmt }))}
                      className={`px-3 py-2.5 rounded-xl text-xs font-semibold border transition-all ${
                        options.output_format === fmt
                          ? "bg-sky-500/20 border-sky-500 text-sky-300 shadow"
                          : "bg-white/[0.02] border-white/[0.06] text-slate-300 hover:bg-white/[0.06]"
                      }`}
                    >
                      {fmt}
                    </button>
                  ))}
                </div>

                {options.output_format === "JPEG" && (
                  <div className="p-3 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                    <label className="text-xs text-slate-300 font-medium">JPEG Matte Background (Transparency)</label>
                    <p className="text-[11px] text-slate-400">
                      JPEG does not support transparency. Transparent pixels will blend against this color:
                    </p>
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={options.matte_color}
                        onChange={(e) => setOptions((prev) => ({ ...prev, matte_color: e.target.value }))}
                        className="w-8 h-8 rounded-lg cursor-pointer bg-transparent border-0"
                      />
                      <input
                        type="text"
                        value={options.matte_color}
                        onChange={(e) => setOptions((prev) => ({ ...prev, matte_color: e.target.value }))}
                        className="bg-black/40 border border-white/10 rounded-xl px-2.5 py-1 text-xs text-white uppercase font-mono"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 5. PRESETS TAB */}
            {activeTab === "presets" && (
              <div className="space-y-4">
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
                  {presetCategories.map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setPresetCategory(cat)}
                      className={`px-2.5 py-1 rounded-lg text-xs whitespace-nowrap transition-all ${
                        presetCategory === cat ? "bg-sky-500 text-white font-semibold" : "bg-white/[0.04] text-slate-400"
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>

                <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                  {filteredPresets.map((p) => (
                    <div
                      key={p.id}
                      onClick={() => handleApplyPreset(p)}
                      className="p-3 rounded-2xl bg-white/[0.02] hover:bg-sky-500/10 border border-white/[0.06] hover:border-sky-500/30 cursor-pointer transition-all flex items-center justify-between"
                    >
                      <div className="space-y-0.5">
                        <p className="text-xs font-semibold text-slate-100">{p.name}</p>
                        <p className="text-[10px] text-slate-400">{p.description}</p>
                        <div className="flex items-center gap-2 text-[10px] text-sky-400 font-mono pt-1">
                          <span>
                            {p.width}×{p.height} {p.unit}
                          </span>
                          <span>•</span>
                          <span>{p.dpi} DPI</span>
                          {p.max_size_kb && (
                            <>
                              <span>•</span>
                              <span>&lt; {p.max_size_kb} KB</span>
                            </>
                          )}
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 6. DPI & PRINT TAB */}
            {activeTab === "dpi" && (
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold text-slate-300">Set DPI (Dots Per Inch)</label>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Modifies print resolution metadata without resampling or corrupting pixel clarity.
                  </p>
                  <div className="grid grid-cols-3 gap-2 mt-2">
                    {[200, 300, 600].map((d) => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => setOptions((prev) => ({ ...prev, dpi: d }))}
                        className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                          options.dpi === d
                            ? "bg-sky-500/20 border-sky-500 text-sky-300"
                            : "bg-white/[0.02] border-white/[0.06] text-slate-300"
                        }`}
                      >
                        {d} DPI
                      </button>
                    ))}
                  </div>
                </div>

                {metadataInfo && (
                  <div className="p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-2 text-xs">
                    <span className="font-semibold text-slate-200">Estimated Print Size @ {options.dpi || 300} DPI</span>
                    <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300">
                      <div>
                        Inches:{" "}
                        <span className="font-mono text-sky-400">
                          {((metadataInfo.basic.width / (options.dpi || 300))).toFixed(2)}" ×{" "}
                          {((metadataInfo.basic.height / (options.dpi || 300))).toFixed(2)}"
                        </span>
                      </div>
                      <div>
                        Centimeters:{" "}
                        <span className="font-mono text-sky-400">
                          {(((metadataInfo.basic.width / (options.dpi || 300)) * 2.54)).toFixed(2)} ×{" "}
                          {(((metadataInfo.basic.height / (options.dpi || 300)) * 2.54)).toFixed(2)} cm
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 7. EXIF & METADATA TAB */}
            {activeTab === "metadata" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-xs font-semibold text-slate-300">Strip EXIF Metadata</label>
                    <p className="text-[11px] text-slate-400">Removes camera serials, location GPS & timestamps for 100% privacy.</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={options.strip_metadata}
                    onChange={(e) => setOptions((prev) => ({ ...prev, strip_metadata: e.target.checked }))}
                    className="w-4 h-4 rounded bg-black/40 border-white/20 text-sky-500 focus:ring-0 cursor-pointer"
                  />
                </div>

                {metadataInfo?.exif?.has_exif ? (
                  <div className="p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-2 text-xs max-h-56 overflow-y-auto">
                    <span className="font-semibold text-slate-200">Discovered Camera & EXIF Data:</span>
                    {metadataInfo.exif.camera.make && (
                      <p className="text-[11px] text-slate-400">
                        Make/Model: <span className="text-slate-200">{metadataInfo.exif.camera.make} {metadataInfo.exif.camera.model}</span>
                      </p>
                    )}
                    {metadataInfo.exif.datetime && (
                      <p className="text-[11px] text-slate-400">
                        Date Taken: <span className="text-slate-200">{metadataInfo.exif.datetime}</span>
                      </p>
                    )}
                    {metadataInfo.exif.exposure.iso && (
                      <p className="text-[11px] text-slate-400">
                        ISO / Shutter: <span className="text-slate-200">ISO {metadataInfo.exif.exposure.iso} • {metadataInfo.exif.exposure.exposure_time}s</span>
                      </p>
                    )}
                    {metadataInfo.exif.gps && (
                      <p className="text-[11px] text-amber-400">
                        ⚠️ Contains GPS Coordinates ({Object.keys(metadataInfo.exif.gps).length} tags)
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">No EXIF or privacy tags detected on this file.</p>
                )}
              </div>
            )}

            {/* 8. ENHANCE TAB */}
            {activeTab === "enhance" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300">Auto Contrast & Levels</span>
                  <input
                    type="checkbox"
                    checked={options.auto_contrast}
                    onChange={(e) => setOptions((prev) => ({ ...prev, auto_contrast: e.target.checked }))}
                    className="w-4 h-4 rounded bg-black/40 border-white/20 text-sky-500 focus:ring-0 cursor-pointer"
                  />
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs text-slate-400">
                      <span>Brightness</span>
                      <span>{Math.round(options.brightness * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.5"
                      max="1.5"
                      step="0.05"
                      value={options.brightness}
                      onChange={(e) => setOptions((prev) => ({ ...prev, brightness: parseFloat(e.target.value) }))}
                      className="w-full accent-sky-500 cursor-pointer"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between text-xs text-slate-400">
                      <span>Contrast</span>
                      <span>{Math.round(options.contrast * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.5"
                      max="1.8"
                      step="0.05"
                      value={options.contrast}
                      onChange={(e) => setOptions((prev) => ({ ...prev, contrast: parseFloat(e.target.value) }))}
                      className="w-full accent-sky-500 cursor-pointer"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between text-xs text-slate-400">
                      <span>Sharpness</span>
                      <span>{Math.round(options.sharpness * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="1.0"
                      max="3.0"
                      step="0.1"
                      value={options.sharpness}
                      onChange={(e) => setOptions((prev) => ({ ...prev, sharpness: parseFloat(e.target.value) }))}
                      className="w-full accent-sky-500 cursor-pointer"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-white/[0.06]">
                  <span className="text-xs font-semibold text-slate-300">Denoise (Smoothing)</span>
                  <input
                    type="checkbox"
                    checked={options.denoise}
                    onChange={(e) => setOptions((prev) => ({ ...prev, denoise: e.target.checked }))}
                    className="w-4 h-4 rounded bg-black/40 border-white/20 text-sky-500 focus:ring-0 cursor-pointer"
                  />
                </div>
              </div>
            )}

            {/* 9. WATERMARK & REDACT TAB */}
            {activeTab === "watermark" && (
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold text-slate-300">Watermark Text</label>
                  <input
                    type="text"
                    value={options.watermark_text || ""}
                    onChange={(e) => setOptions((prev) => ({ ...prev, watermark_text: e.target.value }))}
                    className="mt-1 w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500"
                    placeholder="e.g. Alya Confidential / Draft"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-300">Position</label>
                  <select
                    value={options.watermark_position}
                    onChange={(e) => setOptions((prev) => ({ ...prev, watermark_position: e.target.value as any }))}
                    className="mt-1 w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                  >
                    <option value="bottom-right">Bottom Right</option>
                    <option value="center">Center</option>
                    <option value="top-left">Top Left</option>
                    <option value="top-right">Top Right</option>
                    <option value="bottom-left">Bottom Left</option>
                    <option value="tile">Tile / Repeat Pattern</option>
                  </select>
                </div>

                <div>
                  <div className="flex justify-between text-xs text-slate-400">
                    <span>Opacity</span>
                    <span>{Math.round(options.watermark_opacity * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    value={options.watermark_opacity}
                    onChange={(e) => setOptions((prev) => ({ ...prev, watermark_opacity: parseFloat(e.target.value) }))}
                    className="w-full accent-sky-500 cursor-pointer"
                  />
                </div>
              </div>
            )}

            {/* 10. BATCH TAB */}
            {activeTab === "batch" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-300 font-semibold">Queue ({batchFiles.length} files)</span>
                  {batchFiles.length > 0 && (
                    <button onClick={() => setBatchFiles([])} className="text-rose-400 hover:text-rose-300">
                      Clear Queue
                    </button>
                  )}
                </div>

                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                  {batchFiles.map((bf, idx) => (
                    <div
                      key={idx}
                      className="p-2 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between text-xs text-slate-300"
                    >
                      <span className="truncate max-w-[200px]">{bf.name}</span>
                      <span className="text-[10px] text-slate-400">{(bf.size / 1024).toFixed(1)} KB</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Process Action Button */}
            <div className="pt-2">
              {activeTab !== "batch" ? (
                <button
                  type="button"
                  disabled={!file || isProcessing}
                  onClick={handleProcessImage}
                  className={`w-full py-3.5 px-4 rounded-2xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-xl ${
                    !file || isProcessing
                      ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                      : "bg-gradient-to-r from-sky-500 via-indigo-500 to-purple-600 text-white hover:opacity-95 shadow-sky-500/25 active:scale-[0.99]"
                  }`}
                >
                  {isProcessing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Optimizing Image...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>Process & Apply Pipeline</span>
                    </>
                  )}
                </button>
              ) : (
                <button
                  type="button"
                  disabled={batchFiles.length === 0 || isProcessing}
                  onClick={handleProcessBatch}
                  className={`w-full py-3.5 px-4 rounded-2xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-xl ${
                    batchFiles.length === 0 || isProcessing
                      ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                      : "bg-gradient-to-r from-sky-500 via-indigo-500 to-purple-600 text-white hover:opacity-95 shadow-sky-500/25 active:scale-[0.99]"
                  }`}
                >
                  {isProcessing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Processing Batch Queue...</span>
                    </>
                  ) : (
                    <>
                      <FileArchive className="w-4 h-4" />
                      <span>Process All ({batchFiles.length} Files)</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Preview & Results (7 cols on lg) */}
        <div className="lg:col-span-7 space-y-5">
          {activeTab !== "batch" ? (
            /* Single Image Preview & Stats */
            <div className="space-y-5">
              {previewSrc && processResult?.preview_url ? (
                /* Interactive Before / After Split Slider */
                <BeforeAfterSlider
                  originalSrc={previewSrc}
                  processedSrc={processResult.preview_url}
                  originalLabel={`Original (${(file?.size ? file.size / 1024 : 0).toFixed(1)} KB)`}
                  processedLabel={`Processed (${processResult.metrics?.final_size_kb || 0} KB)`}
                />
              ) : previewSrc ? (
                /* Simple Source Preview */
                <div className="relative w-full h-80 md:h-96 rounded-3xl overflow-hidden bg-black/40 border border-white/[0.08] flex items-center justify-center p-4 shadow-2xl">
                  <img src={previewSrc} alt="Preview" className="max-h-full max-w-full object-contain rounded-xl" />
                  <div className="absolute top-3 left-3 px-3 py-1 rounded-xl text-xs font-semibold bg-black/70 text-slate-200 border border-white/10 backdrop-blur-md">
                    Original Source Preview
                  </div>
                </div>
              ) : (
                /* Empty Placeholder */
                <div className="w-full h-80 md:h-96 rounded-3xl border border-dashed border-white/10 bg-white/[0.01] flex flex-col items-center justify-center p-6 text-center text-slate-500 space-y-2">
                  <FileImage className="w-12 h-12 stroke-[1.2] text-slate-600" />
                  <p className="text-sm font-medium text-slate-400">No image loaded yet</p>
                  <p className="text-xs text-slate-500 max-w-xs">
                    Upload a JPG, PNG, WebP or HEIC file from the left panel to begin.
                  </p>
                </div>
              )}

              {/* Processed Metrics & Download Card */}
              {processResult && processResult.metrics && (
                <div className="rounded-3xl bg-slate-900/80 border border-white/[0.08] p-5 space-y-4 backdrop-blur-xl shadow-xl">
                  {/* Warning Notice if applicable */}
                  {processResult.metrics.warning && (
                    <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                      <span>{processResult.metrics.warning}</span>
                    </div>
                  )}

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="p-3 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Original Size</span>
                      <p className="text-sm font-bold text-slate-200 mt-0.5">
                        {processResult.metrics.original_size_kb} KB
                      </p>
                      <p className="text-[10px] text-slate-500 font-mono">
                        {processResult.metrics.original_dimensions[0]}×{processResult.metrics.original_dimensions[1]} px
                      </p>
                    </div>

                    <div className="p-3 rounded-2xl bg-sky-500/10 border border-sky-500/20">
                      <span className="text-[10px] text-sky-400 uppercase font-semibold">Final Size</span>
                      <p className="text-sm font-bold text-sky-200 mt-0.5">
                        {processResult.metrics.final_size_kb} KB
                      </p>
                      <p className="text-[10px] text-sky-400 font-mono">
                        {processResult.metrics.final_dimensions[0]}×{processResult.metrics.final_dimensions[1]} px
                      </p>
                    </div>

                    <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
                      <span className="text-[10px] text-emerald-400 uppercase font-semibold">Reduction</span>
                      <p className="text-sm font-bold text-emerald-300 mt-0.5">
                        📉 {processResult.metrics.percentage_reduction}%
                      </p>
                      <p className="text-[10px] text-emerald-500 font-medium">Bytes saved</p>
                    </div>

                    <div className="p-3 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">Format & DPI</span>
                      <p className="text-sm font-bold text-slate-200 mt-0.5">
                        {processResult.metrics.output_format}
                      </p>
                      <p className="text-[10px] text-slate-500 font-mono">{processResult.metrics.dpi[0]} DPI</p>
                    </div>
                  </div>

                  {/* Download Button */}
                  <a
                    href={processResult.download_url}
                    download={processResult.filename}
                    className="w-full py-3.5 px-4 rounded-2xl font-bold text-sm bg-gradient-to-r from-emerald-500 to-teal-600 text-white flex items-center justify-center gap-2 hover:opacity-95 shadow-lg shadow-emerald-500/20 active:scale-[0.99] transition-all"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Processed Image ({processResult.filename})</span>
                  </a>
                </div>
              )}
            </div>
          ) : (
            /* Bulk Batch Results View */
            <div className="space-y-4">
              {batchResult ? (
                <div className="rounded-3xl bg-slate-900/80 border border-white/[0.08] p-5 space-y-4 backdrop-blur-xl shadow-xl">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-white">Batch Processing Completed</h3>
                      <p className="text-xs text-slate-400">
                        {batchResult.successful} of {batchResult.total} files processed successfully
                      </p>
                    </div>

                    {batchResult.zip_download_url && (
                      <a
                        href={batchResult.zip_download_url}
                        download="alya_processed_images.zip"
                        className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 text-white text-xs font-bold shadow-lg shadow-sky-500/20 hover:opacity-95"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download All (ZIP)</span>
                      </a>
                    )}
                  </div>

                  {/* Individual Batch Items */}
                  <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                    {batchResult.results.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-2xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between text-xs"
                      >
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            {item.success ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                            ) : (
                              <AlertTriangle className="w-4 h-4 text-rose-400" />
                            )}
                            <span className="font-semibold text-slate-200">{item.source_filename}</span>
                          </div>
                          {item.metrics && (
                            <p className="text-[11px] text-slate-400 font-mono">
                              {item.metrics.original_size_kb} KB → {item.metrics.final_size_kb} KB ({item.metrics.percentage_reduction}% reduction)
                            </p>
                          )}
                          {item.error && <p className="text-[11px] text-rose-400">{item.error}</p>}
                        </div>

                        {item.download_url && (
                          <a
                            href={item.download_url}
                            download={item.filename}
                            className="p-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-sky-400 border border-white/[0.06]"
                            title="Download single file"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="w-full h-80 rounded-3xl border border-dashed border-white/10 bg-white/[0.01] flex flex-col items-center justify-center p-6 text-center text-slate-500 space-y-2">
                  <FileArchive className="w-12 h-12 stroke-[1.2] text-slate-600" />
                  <p className="text-sm font-medium text-slate-400">Bulk Queue Idle</p>
                  <p className="text-xs text-slate-500 max-w-xs">
                    Add multiple files to the batch queue and click "Process All" to generate a ZIP package.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
