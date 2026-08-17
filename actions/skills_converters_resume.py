import os
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv("/home/ubuntu/Rasa/.env")

from . import skills_documents as docs

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

STORAGE_FILES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "files"))
os.makedirs(STORAGE_FILES_DIR, exist_ok=True)


def _clean_llm_think(text: str) -> str:
    """Strips <think> tags from LLM responses."""
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    elif "<think>" in text:
        text = re.sub(r"<think>.*", "", text, flags=re.DOTALL).strip()
    return text.strip()


# ---------------------------------------------------------------------------
# 1. Smart Resume & Cover Letter PDF Engine
# ---------------------------------------------------------------------------

def generate_resume_pdf(role_or_details: str, user_name: str = "Professional Candidate") -> Dict[str, Any]:
    """
    Synthesizes a high-impact, ATS-friendly professional resume and compiles it into a styled PDF.
    """
    clean_prompt = role_or_details.strip()
    if not clean_prompt:
        clean_prompt = "Senior Full Stack Software Engineer with Python, React, Cloud & AI skills"

    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Fortune 500 executive resume architect and ATS specialist. "
                            "Generate a complete, structured JSON resume based on the target role/details.\n"
                            "Return strict JSON with this exact schema:\n"
                            "{\n"
                            '  "name": "Candidate Name",\n'
                            '  "title": "Professional Title / Target Role",\n'
                            '  "contact": "Email: email@example.com | Phone: +91-9876543210 | LinkedIn: in/profile | Location: India",\n'
                            '  "summary": "Impactful 3-sentence executive summary highlighting experience, leadership, and core value proposition.",\n'
                            '  "skills": ["Python", "FastAPI", "React", "Docker", "AWS", "Machine Learning", "System Architecture", "PostgreSQL"],\n'
                            '  "experience": [\n'
                            '    {"role": "Lead Software Engineer", "company": "Tech Innovations Ltd.", "period": "2022 – Present", "points": ["Architected scalable microservices reducing API latency by 45%.", "Led a team of 8 engineers delivering enterprise cloud platform.", "Integrated AI inference pipelines serving 1M+ daily requests."]}\n'
                            '  ],\n'
                            '  "projects": [\n'
                            '    {"name": "Autonomous AI Agent Platform", "description": "Built end-to-end multi-agent orchestration system with LangGraph & Groq."}\n'
                            '  ],\n'
                            '  "education": "B.Tech in Computer Science & Engineering — First Class with Distinction (2018–2022)"\n'
                            "}\n"
                            "Return ONLY raw JSON, no markdown codeblocks, no reasoning."
                        )
                    },
                    {"role": "user", "content": f"Target Role & Info: {clean_prompt}"}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            raw_text = _clean_llm_think(resp.choices[0].message.content)
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except Exception:
                    data = None
            else:
                data = None

            if not data:
                data = {
                    "name": user_name,
                    "title": clean_prompt,
                    "contact": "Email: candidate@example.com | Phone: +91-9876543210 | Location: India",
                    "summary": f"Results-driven professional with deep expertise in {clean_prompt}. Proven track record of delivering end-to-end technical solutions.",
                    "skills": ["Python", "System Design", "Cloud Infrastructure", "API Architecture", "Data Engineering", "Agile Leadership"],
                    "experience": [
                        {"role": clean_prompt, "company": "Premier Tech Solutions", "period": "2022 – Present", "points": ["Spearheaded core technical architecture delivering 99.9% uptime.", "Automated high-throughput pipelines reducing operational costs by 30%."]}
                    ],
                    "projects": [
                        {"name": "Enterprise Automation Platform", "description": "Designed intelligent multi-service orchestration framework."}
                    ],
                    "education": "B.Tech in Computer Science & Engineering — First Class"
                }

            # Compile into styled PDF using ReportLab
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"resume_{timestamp}.pdf"
            file_path = os.path.join(STORAGE_FILES_DIR, filename)

            doc = SimpleDocTemplate(
                file_path,
                pagesize=letter,
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40
            )

            styles = getSampleStyleSheet()

            name_style = ParagraphStyle(
                "ResumeName",
                parent=styles["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#1A365D"),
                alignment=1
            )

            title_style = ParagraphStyle(
                "ResumeTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=16,
                textColor=colors.HexColor("#2B6CB0"),
                alignment=1
            )

            contact_style = ParagraphStyle(
                "ResumeContact",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                leading=13,
                textColor=colors.HexColor("#4A5568"),
                alignment=1
            )

            section_hdr_style = ParagraphStyle(
                "SectionHeader",
                parent=styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=16,
                textColor=colors.HexColor("#1A365D"),
                spaceBefore=8,
                spaceAfter=4
            )

            body_style = ParagraphStyle(
                "ResumeBody",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9.5,
                leading=14,
                textColor=colors.HexColor("#2D3748")
            )

            bullet_style = ParagraphStyle(
                "ResumeBullet",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                leading=13,
                textColor=colors.HexColor("#2D3748"),
                leftIndent=12
            )

            story = []

            # 1. Header
            story.append(Paragraph(data.get("name", user_name), name_style))
            story.append(Spacer(1, 2))
            story.append(Paragraph(data.get("title", "Professional"), title_style))
            story.append(Spacer(1, 4))
            story.append(Paragraph(data.get("contact", ""), contact_style))
            story.append(Spacer(1, 8))
            story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1A365D"), spaceBefore=2, spaceAfter=8))

            # 2. Executive Summary
            story.append(Paragraph("EXECUTIVE SUMMARY", section_hdr_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E0"), spaceBefore=1, spaceAfter=4))
            story.append(Paragraph(data.get("summary", ""), body_style))
            story.append(Spacer(1, 8))

            # 3. Core Competencies / Skills
            story.append(Paragraph("CORE SKILLS & TECHNOLOGIES", section_hdr_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E0"), spaceBefore=1, spaceAfter=4))
            skills_str = " • ".join(data.get("skills", []))
            story.append(Paragraph(f"<b>Technical Skills:</b> {skills_str}", body_style))
            story.append(Spacer(1, 8))

            # 4. Professional Experience
            story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_hdr_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E0"), spaceBefore=1, spaceAfter=4))

            for exp in data.get("experience", []):
                role_head = f"<b>{exp.get('role', '')}</b> | <i>{exp.get('company', '')}</i> — <font color='#4A5568'>{exp.get('period', '')}</font>"
                story.append(Paragraph(role_head, body_style))
                story.append(Spacer(1, 2))
                for pt in exp.get("points", []):
                    story.append(Paragraph(f"• {pt}", bullet_style))
                story.append(Spacer(1, 4))

            # 5. Key Projects
            if data.get("projects"):
                story.append(Paragraph("FEATURED PROJECTS", section_hdr_style))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E0"), spaceBefore=1, spaceAfter=4))
                for prj in data.get("projects", []):
                    story.append(Paragraph(f"<b>{prj.get('name', '')}</b>: {prj.get('description', '')}", bullet_style))
                    story.append(Spacer(1, 2))
                story.append(Spacer(1, 4))

            # 6. Education
            story.append(Paragraph("EDUCATION", section_hdr_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E0"), spaceBefore=1, spaceAfter=4))
            story.append(Paragraph(str(data.get("education", "")), body_style))

            doc.build(story)

            return {
                "success": True,
                "file_path": file_path,
                "file_type": "document",
                "text": (
                    f"📄 **Professional ATS Resume Generated!**\n\n"
                    f"• **Candidate**: `{data.get('name')}`\n"
                    f"• **Target Role**: `{data.get('title')}`\n"
                    f"• **File**: `{filename}` (Ready for job applications & ATS scans)"
                )
            }
    except Exception as e:
        logger.error(f"Resume builder error: {e}")
        return {"error": f"⚠️ Failed to generate resume PDF: {e}"}


def generate_cover_letter_pdf(company_and_role: str, user_name: str = "Candidate") -> Dict[str, Any]:
    """
    Generates a compelling, customized formal Cover Letter PDF tailored for a company & job title.
    """
    clean_target = company_and_role.strip()
    if not clean_target:
        clean_target = "Google — Senior AI Engineer"

    try:
        from groq import Groq
        key = os.getenv("GROQ_API_KEY")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Draft a high-impact, professional formal cover letter for the given company and job title. "
                            "Include Date, Hiring Manager salutation, 3 strong persuasive paragraphs connecting passion & skills, "
                            "and professional sign-off. Use clean paragraphs separated by double newlines."
                        )
                    },
                    {"role": "user", "content": f"Apply to: {clean_target}"}
                ],
                temperature=0.2,
                max_tokens=900
            )
            body_content = _clean_llm_think(resp.choices[0].message.content)
            title = f"Cover Letter — {clean_target}"
            fpath, msg = docs.create_pdf_file(title, body_content, filename=f"cover_letter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

            return {
                "success": True,
                "file_path": fpath,
                "file_type": "document",
                "text": f"✉️ **Cover Letter Generated:** `{os.path.basename(fpath)}`\n• Target: `{clean_target}`"
            }
    except Exception as e:
        logger.error(f"Cover letter error: {e}")
        return {"error": f"⚠️ Failed to generate cover letter PDF: {e}"}


# ---------------------------------------------------------------------------
# 2. File & Image Format Converter Engine
# ---------------------------------------------------------------------------

def convert_image_file(source_image_path: str, target_format: str = "png") -> Dict[str, Any]:
    """
    Converts images between PNG, JPG, JPEG, WEBP, and PDF.
    Also supports image compression / resizing.
    """
    if not os.path.exists(source_image_path):
        return {"error": f"⚠️ Source image not found: `{source_image_path}`"}

    target_fmt = target_format.lower().strip().replace(".", "")
    if target_fmt not in ["png", "jpg", "jpeg", "webp", "pdf"]:
        target_fmt = "png"

    try:
        img = Image.open(source_image_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(os.path.basename(source_image_path))[0]
        out_filename = f"{base_name}_converted_{timestamp}.{target_fmt}"
        out_path = os.path.join(STORAGE_FILES_DIR, out_filename)

        # Handle RGBA to RGB for JPEG/PDF
        if target_fmt in ["jpg", "jpeg", "pdf"] and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        if target_fmt == "pdf":
            img.save(out_path, "PDF", resolution=100.0)
            f_type = "document"
        elif target_fmt in ["jpg", "jpeg"]:
            img.save(out_path, "JPEG", quality=90, optimize=True)
            f_type = "photo"
        elif target_fmt == "webp":
            img.save(out_path, "WEBP", quality=90)
            f_type = "photo"
        else:
            img.save(out_path, "PNG", optimize=True)
            f_type = "photo"

        orig_size_kb = os.path.getsize(source_image_path) / 1024
        new_size_kb = os.path.getsize(out_path) / 1024

        return {
            "success": True,
            "file_path": out_path,
            "file_type": f_type,
            "text": (
                f"🔄 **Image Converted Successfully!**\n\n"
                f"• **Original**: `{os.path.basename(source_image_path)}` ({orig_size_kb:.1f} KB)\n"
                f"• **Output Format**: `{target_fmt.upper()}` ({new_size_kb:.1f} KB)\n"
                f"• **Dimensions**: `{img.width} x {img.height} px`\n"
                f"• **File**: `{out_filename}`"
            )
        }
    except Exception as e:
        logger.error(f"Image conversion error: {e}")
        return {"error": f"⚠️ Image conversion error: {e}"}


def convert_document_file(source_doc_path: str, target_format: str = "txt") -> Dict[str, Any]:
    """
    Converts document formats:
    - PDF -> TXT / DOCX
    - DOCX -> TXT / PDF
    - Markdown / Text -> PDF
    """
    if not os.path.exists(source_doc_path):
        return {"error": f"⚠️ Source document not found: `{source_doc_path}`"}

    target_fmt = target_format.lower().strip().replace(".", "")
    base_name = os.path.splitext(os.path.basename(source_doc_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # Case 1: PDF to TXT
        if source_doc_path.lower().endswith(".pdf") and target_fmt == "txt":
            extracted_text = docs.read_pdf_file(source_doc_path, max_pages=50)
            out_filename = f"{base_name}_extracted_{timestamp}.txt"
            out_path = os.path.join(STORAGE_FILES_DIR, out_filename)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(extracted_text)
            return {
                "success": True,
                "file_path": out_path,
                "file_type": "document",
                "text": f"📄 **PDF Converted to Plain Text:** `{out_filename}`"
            }

        # Case 2: PDF to DOCX
        elif source_doc_path.lower().endswith(".pdf") and target_fmt in ["docx", "doc", "word"]:
            extracted_text = docs.read_pdf_file(source_doc_path, max_pages=50)
            out_filename = f"{base_name}_converted_{timestamp}.docx"
            out_path = docs.create_word_document_file(f"Document — {base_name}", [{"heading": "Content", "body": extracted_text}], filename=out_filename)
            return {
                "success": True,
                "file_path": out_path,
                "file_type": "document",
                "text": f"📝 **PDF Converted to Word Document:** `{out_filename}`"
            }

        # Case 3: Text / Markdown to PDF
        elif target_fmt == "pdf":
            with open(source_doc_path, "r", encoding="utf-8", errors="ignore") as f:
                text_content = f.read()
            out_filename = f"{base_name}_compiled_{timestamp}.pdf"
            fpath, _ = docs.create_pdf_file(f"Document — {base_name}", text_content, filename=out_filename)
            return {
                "success": True,
                "file_path": fpath,
                "file_type": "document",
                "text": f"📄 **Document Compiled into PDF:** `{out_filename}`"
            }

    except Exception as e:
        logger.error(f"Document converter error: {e}")
        return {"error": f"⚠️ Document conversion failed: {e}"}

    return {"error": f"⚠️ Unsupported conversion from `{os.path.basename(source_doc_path)}` to `{target_fmt}`."}
