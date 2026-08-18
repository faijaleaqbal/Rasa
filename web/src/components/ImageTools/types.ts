export type ToolTab =
  | "compress"
  | "resize"
  | "crop"
  | "convert"
  | "presets"
  | "dpi"
  | "metadata"
  | "enhance"
  | "watermark"
  | "batch";

export interface PresetItem {
  id: string;
  name: string;
  category: string;
  description: string;
  width: number;
  height: number;
  unit: string;
  dpi: number;
  format: string;
  max_size_kb?: number;
  min_size_kb?: number;
  maintain_aspect: boolean;
  aspect_ratio?: string;
  quality: number;
}

export interface ImageMetrics {
  original_size_bytes: number;
  original_size_kb: number;
  original_size_mb: number;
  final_size_bytes: number;
  final_size_kb: number;
  final_size_mb: number;
  percentage_reduction: number;
  original_dimensions: [number, number];
  final_dimensions: [number, number];
  original_format: string;
  output_format: string;
  dpi: [number, number];
  quality_used: number;
  warning?: string;
}

export interface ProcessResponse {
  success: boolean;
  token?: string;
  filename?: string;
  mime_type?: string;
  download_url?: string;
  preview_url?: string;
  metrics?: ImageMetrics;
  exif?: any;
  error?: string;
}

export interface BatchItemResult extends ProcessResponse {
  source_filename: string;
}

export interface BatchResponse {
  success: boolean;
  total: number;
  successful: number;
  failed: number;
  results: BatchItemResult[];
  zip_token?: string;
  zip_download_url?: string;
  error?: string;
}

export interface ImageMetadataResponse {
  success: boolean;
  filename: string;
  basic: {
    format: string;
    mime_type: string;
    width: number;
    height: number;
    file_size_kb: number;
    has_alpha: boolean;
    dpi_x: number;
    dpi_y: number;
  };
  print_dimensions: {
    dpi: number;
    inches: { width: number; height: number };
    cm: { width: number; height: number };
    mm: { width: number; height: number };
  };
  exif?: {
    has_exif: boolean;
    camera: { make?: string; model?: string };
    exposure: { exposure_time?: string; f_number?: string; iso?: string; focal_length?: string };
    datetime?: string;
    software?: string;
    gps?: Record<string, string>;
  };
  error?: string;
}

export interface PipelineOptions {
  preset_id?: string;
  // Compress
  target_size_kb?: number;
  quality?: number;
  // Resize
  target_width?: number;
  target_height?: number;
  unit: "px" | "cm" | "mm" | "in";
  maintain_aspect: boolean;
  resample_filter: "lanczos" | "bicubic" | "bilinear" | "box" | "nearest";
  scale_mode: "fit" | "stretch" | "cover";
  // Crop & Transform
  crop_x?: number;
  crop_y?: number;
  crop_width?: number;
  crop_height?: number;
  crop_aspect_ratio?: string;
  crop_shape: "rect" | "square" | "circle";
  rotation_angle: number;
  flip_horizontal: boolean;
  flip_vertical: boolean;
  // Convert
  output_format?: "JPEG" | "PNG" | "WEBP";
  matte_color: string;
  // DPI
  dpi?: number;
  // Enhance
  auto_contrast: boolean;
  brightness: number;
  contrast: number;
  sharpness: number;
  color_balance: number;
  denoise: boolean;
  upscale_factor: number;
  // Watermark
  watermark_text?: string;
  watermark_opacity: number;
  watermark_position: "center" | "top-left" | "top-right" | "bottom-left" | "bottom-right" | "tile";
  privacy_blur_box?: [number, number, number, number];
  privacy_effect: "blur" | "pixelate";
  // Privacy
  strip_metadata: boolean;
}
