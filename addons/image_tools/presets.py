"""
Centralized, configurable image presets for documents, passport photos,
visas, social media assets, and government portal uploads.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class Preset:
    id: str
    name: str
    category: str
    description: str
    width: int
    height: int
    unit: str  # "px", "cm", "mm", "in"
    dpi: int = 300
    format: str = "JPEG"
    max_size_kb: Optional[int] = None
    min_size_kb: Optional[int] = None
    maintain_aspect: bool = True
    aspect_ratio: Optional[str] = None
    quality: int = 90

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Default Presets Registry
DEFAULT_PRESETS: List[Preset] = [
    # 1. Passports & Visas
    Preset(
        id="passport_india",
        name="Indian Passport / Visa Photo",
        category="Passport & Visa",
        description="Standard 3.5 × 4.5 cm photo at 300 DPI for Indian passports, OCI, and visas",
        width=413,
        height=531,
        unit="px",
        dpi=300,
        format="JPEG",
        max_size_kb=200,
        aspect_ratio="3.5:4.5",
    ),
    Preset(
        id="visa_us",
        name="US Visa / Passport (2 × 2 inch)",
        category="Passport & Visa",
        description="Official 2 × 2 inches (600 × 600 px) photo at 300 DPI for US DS-160 & Passport",
        width=600,
        height=600,
        unit="px",
        dpi=300,
        format="JPEG",
        max_size_kb=240,
        aspect_ratio="1:1",
    ),
    Preset(
        id="passport_uk_schengen",
        name="UK / Schengen / EU Visa",
        category="Passport & Visa",
        description="Standard 3.5 × 4.5 cm (413 × 531 px) biometric photo at 300 DPI for Schengen and UK",
        width=413,
        height=531,
        unit="px",
        dpi=300,
        format="JPEG",
        max_size_kb=200,
        aspect_ratio="3.5:4.5",
    ),
    Preset(
        id="photo_3x4_in",
        name="3 × 4 inch Photo",
        category="Passport & Visa",
        description="Standard 3 × 4 inch photo at 300 DPI (900 × 1200 px)",
        width=900,
        height=1200,
        unit="px",
        dpi=300,
        format="JPEG",
        aspect_ratio="3:4",
    ),
    Preset(
        id="photo_600x600",
        name="600 × 600 px Avatar / ID",
        category="Passport & Visa",
        description="Square 600 × 600 px digital ID & avatar",
        width=600,
        height=600,
        unit="px",
        dpi=300,
        format="JPEG",
        aspect_ratio="1:1",
    ),

    # 2. Documents & Paper Sizes
    Preset(
        id="doc_a4_300dpi",
        name="A4 Document (300 DPI - High Quality)",
        category="Documents",
        description="Standard A4 sheet (210 × 297 mm) at 300 DPI (2480 × 3508 px) for crisp printing",
        width=2480,
        height=3508,
        unit="px",
        dpi=300,
        format="PNG",
        aspect_ratio="1:1.414",
    ),
    Preset(
        id="doc_a4_150dpi",
        name="A4 Document (150 DPI - Web / Email)",
        category="Documents",
        description="A4 sheet (1240 × 1754 px) optimized for digital sharing and email attachments",
        width=1240,
        height=1754,
        unit="px",
        dpi=150,
        format="JPEG",
        max_size_kb=500,
        aspect_ratio="1:1.414",
    ),
    Preset(
        id="doc_a5_300dpi",
        name="A5 Booklet / Flyer (300 DPI)",
        category="Documents",
        description="A5 standard page (148 × 210 mm) at 300 DPI (1748 × 2480 px)",
        width=1748,
        height=2480,
        unit="px",
        dpi=300,
        format="PNG",
        aspect_ratio="1:1.414",
    ),
    Preset(
        id="doc_letter_300dpi",
        name="US Letter Document (300 DPI)",
        category="Documents",
        description="8.5 × 11 inch sheet at 300 DPI (2550 × 3300 px)",
        width=2550,
        height=3300,
        unit="px",
        dpi=300,
        format="PNG",
        aspect_ratio="8.5:11",
    ),

    # 3. Government Portals & Upload Limits
    Preset(
        id="govt_signature_20kb",
        name="Govt Portal Signature (< 20 KB)",
        category="Govt & Exam Portals",
        description="Signature image compressed to strictly under 20 KB (typically 200 × 100 px)",
        width=300,
        height=150,
        unit="px",
        dpi=200,
        format="JPEG",
        max_size_kb=20,
        quality=80,
    ),
    Preset(
        id="govt_photo_50kb",
        name="Govt Portal Photo (< 50 KB)",
        category="Govt & Exam Portals",
        description="Passport-style upload strictly compressed under 50 KB (UPSC, SSC, IBPS, NTA)",
        width=350,
        height=450,
        unit="px",
        dpi=200,
        format="JPEG",
        max_size_kb=50,
        quality=80,
    ),
    Preset(
        id="govt_doc_100kb",
        name="Govt Document Scan (< 100 KB)",
        category="Govt & Exam Portals",
        description="Scan compression strictly under 100 KB for online certificates & ID proofs",
        width=1000,
        height=1400,
        unit="px",
        dpi=150,
        format="JPEG",
        max_size_kb=100,
        quality=75,
    ),

    # 4. Social Media
    Preset(
        id="social_ig_post",
        name="Instagram Post (1:1 Square)",
        category="Social Media",
        description="1080 × 1080 px high-res square post",
        width=1080,
        height=1080,
        unit="px",
        dpi=72,
        format="JPEG",
        aspect_ratio="1:1",
    ),
    Preset(
        id="social_ig_portrait",
        name="Instagram Portrait (4:5)",
        category="Social Media",
        description="1080 × 1350 px vertical feed post",
        width=1080,
        height=1350,
        unit="px",
        dpi=72,
        format="JPEG",
        aspect_ratio="4:5",
    ),
    Preset(
        id="social_ig_story",
        name="Instagram Story / Reel (9:16)",
        category="Social Media",
        description="1080 × 1920 px full-screen mobile format",
        width=1080,
        height=1920,
        unit="px",
        dpi=72,
        format="JPEG",
        aspect_ratio="9:16",
    ),
    Preset(
        id="social_yt_thumb",
        name="YouTube Thumbnail (16:9)",
        category="Social Media",
        description="1280 × 720 px HD thumbnail (< 2 MB)",
        width=1280,
        height=720,
        unit="px",
        dpi=72,
        format="JPEG",
        max_size_kb=2000,
        aspect_ratio="16:9",
    ),
    Preset(
        id="social_x_header",
        name="X / Twitter Header Banner",
        category="Social Media",
        description="1500 × 500 px profile header banner (3:1)",
        width=1500,
        height=500,
        unit="px",
        dpi=72,
        format="JPEG",
        aspect_ratio="3:1",
    ),
    Preset(
        id="social_linkedin_banner",
        name="LinkedIn Profile Banner",
        category="Social Media",
        description="1584 × 396 px (4:1) professional banner",
        width=1584,
        height=396,
        unit="px",
        dpi=72,
        format="JPEG",
        aspect_ratio="4:1",
    ),
    Preset(
        id="social_fb_cover",
        name="Facebook Cover Photo",
        category="Social Media",
        description="820 × 312 px desktop & mobile optimized cover",
        width=820,
        height=312,
        unit="px",
        dpi=72,
        format="JPEG",
        aspect_ratio="820:312",
    ),
]


class PresetRegistry:
    """Registry allowing dynamic registration and retrieval of image presets."""

    def __init__(self, presets: Optional[List[Preset]] = None):
        self._presets: Dict[str, Preset] = {}
        for p in (presets or DEFAULT_PRESETS):
            self.register(p)

    def register(self, preset: Preset) -> None:
        self._presets[preset.id] = preset

    def get(self, preset_id: str) -> Optional[Preset]:
        return self._presets.get(preset_id)

    def list_all(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._presets.values()]

    def list_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        res: Dict[str, List[Dict[str, Any]]] = {}
        for p in self._presets.values():
            res.setdefault(p.category, []).append(p.to_dict())
        return res


# Global singleton instance
preset_registry = PresetRegistry()
