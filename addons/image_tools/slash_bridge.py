"""
Bridge for Alya Telegram / Chatbot slash commands to invoke Image Tools engine.
"""

import os
import io
import re
from typing import Tuple, Optional
from PIL import Image

from .pipeline import process_image_pipeline
from .presets import preset_registry
from .security import ephemeral_store


def handle_image_tool_command(cmd: str, args_str: str) -> Tuple[bool, str, Optional[str], str]:
    """
    Executes image processing commands from Telegram / web chat.
    Returns (handled, markdown_text, file_path_or_none, file_type).
    """
    cmd = cmd.lower()

    if cmd in ["/imagetools", "/imagehelp", "/phototools"]:
        help_msg = (
            "🖼️ **Alya Production Image Tools Studio** 🖼️\n\n"
            "**Available Image Slash Commands:**\n"
            "• `/compress <file_path> [target_kb_or_quality]` — Compress to exact KB (e.g. `50kb`, `100kb`) or quality %\n"
            "• `/resize <file_path> <width> <height> [px|cm|mm|in]` — Smart resize with aspect ratio preservation\n"
            "• `/crop <file_path> <1:1|4:3|16:9|square|circle>` — Aspect ratio & circular shape crop\n"
            "• `/convert <file_path> <jpg|png|webp>` — Lossless & transparent format converter\n"
            "• `/passport <file_path> [india|us|uk|schengen]` — 300 DPI official passport & visa specs\n"
            "• `/dpi <file_path> <200|300|600>` — DPI metadata reader & modifier\n"
            "• `/presets` — View all document, passport, and social media presets\n\n"
            "💡 *You can also use the full interactive Web Image Studio in the Alya Web Dashboard!*"
        )
        return (True, help_msg, None, "text")

    if cmd in ["/presets", "/imagepresets"]:
        categories = preset_registry.list_by_category()
        lines = ["📋 **Alya Image Studio — Built-in Presets:**\n"]
        for cat, items in categories.items():
            lines.append(f"**{cat}:**")
            for item in items:
                lines.append(f"• `{item['id']}`: **{item['name']}** ({item['width']}×{item['height']} {item['unit']} @ {item['dpi']} DPI)")
            lines.append("")
        return (True, "\n".join(lines), None, "text")

    if cmd in ["/passport", "/visa"]:
        parts = args_str.split()
        if not parts:
            return (
                True,
                "🪪 **Passport & Visa Photo Maker Usage:** `/passport <file_path> [india|us|uk|schengen]`\nExample: `/passport /path/to/my_photo.jpg india`",
                None,
                "text",
            )
        file_path = parts[0]
        preset_choice = parts[1].lower() if len(parts) > 1 else "india"

        preset_id = "passport_india"
        if "us" in preset_choice:
            preset_id = "visa_us"
        elif "uk" in preset_choice or "schengen" in preset_choice:
            preset_id = "passport_uk_schengen"
        elif "600" in preset_choice:
            preset_id = "photo_600x600"

        if not os.path.exists(file_path):
            return (True, f"❌ File not found at `{file_path}`. Please verify path or upload photo.", None, "text")

        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()

            res = process_image_pipeline(
                image_bytes=raw_bytes,
                filename=os.path.basename(file_path),
                preset_id=preset_id,
            )

            if not res.get("success"):
                return (True, f"❌ Processing failed: {res.get('error')}", None, "text")

            # Save output to temporary file
            out_token = res["token"]
            store_item = ephemeral_store.get(out_token)
            out_file = f"/tmp/{res['filename']}"
            with open(out_file, "wb") as out_f:
                out_f.write(store_item.data)

            m = res["metrics"]
            text = (
                f"✅ **Passport / Visa Photo Created Successfully!**\n"
                f"• **Preset:** {preset_registry.get(preset_id).name}\n"
                f"• **Dimensions:** {m['final_dimensions'][0]} × {m['final_dimensions'][1]} px\n"
                f"• **DPI:** {m['dpi'][0]} DPI\n"
                f"• **File Size:** {m['final_size_kb']} KB\n"
                f"• **Format:** {m['output_format']}"
            )
            return (True, text, out_file, "photo")
        except Exception as e:
            return (True, f"❌ Error processing passport photo: {str(e)}", None, "text")

    return (False, "", None, "text")
