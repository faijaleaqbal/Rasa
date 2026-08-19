"""
Universal Puzzle & Visual Question Solver Module for Alya AI.

Features:
1. Deterministic Mastermind / "Guess the Code" constraint solver.
2. Structured natural language and OCR clue parser.
3. Multi-pass image OCR + Multimodal Vision reasoning.
4. Context-aware emoji selection (🔐 for codes, 🧩 for logic, 📐 for math, ⚡ for physics, etc.).
5. Clear, concise answer formatting (final answer first, short step-by-step verification).
"""

import os
import re
import time
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Set
import requests
from PIL import Image, ImageEnhance, ImageOps

from . import llm_provider

logger = logging.getLogger(__name__)

WORD_TO_NUM: Dict[str, int] = {
    "zero": 0, "none": 0, "nothing": 0, "no": 0, "neither": 0, "0": 0,
    "one": 1, "1": 1,
    "two": 2, "2": 2, "both": 2,
    "three": 3, "3": 3,
    "four": 4, "4": 4,
    "five": 5, "5": 5,
    "six": 6, "6": 6,
}


@dataclass
class PuzzleClue:
    guess: str
    text: str
    total_correct: int
    well_placed: int
    wrong_placed: int = 0
    is_absent: bool = False

    def __post_init__(self):
        if self.wrong_placed == 0 and self.total_correct > self.well_placed:
            self.wrong_placed = self.total_correct - self.well_placed


def clean_digit_string(raw: str) -> str:
    """Cleans OCR noise in digit strings (e.g. 'O' -> '0', 'l'/'I' -> '1', 'S' -> '5', 'B' -> '8')."""
    cleaned = raw.strip()
    substitutions = {
        'O': '0', 'o': '0', 'D': '0', 'Q': '0',
        'l': '1', 'I': '1', '|': '1', '!': '1', 'i': '1', 'T': '7',
        'Z': '2', 'z': '2',
        'S': '5', 's': '5',
        'B': '8',
        'g': '9', 'q': '9',
    }
    res = []
    for ch in cleaned:
        if ch.isdigit():
            res.append(ch)
        elif ch in substitutions:
            res.append(substitutions[ch])
    return "".join(res)


def normalize_ocr_clue_text(text: str) -> str:
    """Normalizes OCR artifacts, concatenated words, and markdown formatting."""
    # Strip markdown formatting
    text = text.replace("**", " ").replace("`", " ").replace("*", " ").replace("~~", " ").replace("__", " ")

    # Common OCR word concatenations
    text = re.sub(r"\bnumbers?(are|is|incorrect|correct)\b", r"numbers \1", text, flags=re.I)
    text = re.sub(r"\bdigits?(are|is|incorrect|correct)\b", r"digits \1", text, flags=re.I)
    text = re.sub(r"\b(all|no|two|three|four|both)(numbers?|digits?|are)\b", r"\1 \2", text, flags=re.I)
    text = re.sub(r"\b(but|and)(only|both|all|one|two|three)\b", r"\1 \2", text, flags=re.I)
    text = re.sub(r"\b(only)(one|two|three|1|2|3)\b", r"\1 \2", text, flags=re.I)
    text = re.sub(r"\b(is|are)(in|the|wrong|correct)\b", r"\1 \2", text, flags=re.I)
    text = re.sub(r"\b(in)(the|wrong|correct)\b", r"\1 \2", text, flags=re.I)
    text = re.sub(r"\b(the)(wrong|correct|right)\b", r"\1 \2", text, flags=re.I)
    text = re.sub(r"\b(both|all)(are|in)\b", r"\1 \2", text, flags=re.I)
    text = re.sub(r"\b(are)(incorrect|correct)\b", r"\1 \2", text, flags=re.I)
    text = re.sub(r"\b(in\s*correct)\b", r"incorrect", text, flags=re.I)
    return text.strip()


def parse_single_clue_line(line: str, default_length: int = 3) -> Optional[PuzzleClue]:
    """
    Parses a single line of text into a PuzzleClue constraint.
    Handles various formats:
      - 079 → All numbers are incorrect.
      - 165: Two numbers are correct, but only one is in the correct position.
      - 365 - Two numbers are correct, but both are in the wrong positions.
      - [6 8 2] One number is correct and well placed.
    """
    clean_line = normalize_ocr_clue_text(line.strip())
    if not clean_line or len(clean_line) < 3:
        return None

    # Strip leading bullets or numbering e.g. "1. ", "• ", "- " (do NOT strip guess digits)
    clean_line = re.sub(r"^([•\*\>\-–—#]|\d+[\.\)])\s*", "", clean_line).strip()

    # Match guess digits at the start, e.g. "079", "[1 6 5]", "3-5-9", "359:"
    m = re.match(r"^[\[\(]?\s*([0-9OlISZBgzq\s\-–,]{2,8})\s*[\]\)]?\s*[:\->–|—=→]\s*(.*)$", clean_line)
    if not m:
        # Match digits followed by space and clue text
        m = re.match(r"^[\[\(]?\s*([0-9OlISZBgzq]{3,6})\s*[\]\)]?\s+(.*)$", clean_line)

    if not m:
        return None

    raw_guess, clue_text = m.groups()
    guess = clean_digit_string(raw_guess)
    if len(guess) < 2:
        return None

    clue_lower = clue_text.lower().strip()

    # 1. All numbers are incorrect / Nothing is correct
    if any(k in clue_lower for k in [
        "all numbers are incorrect", "all digits are wrong", "all incorrect", "nothing is correct",
        "nothing is right", "all are wrong", "none of the numbers", "all numbers incorrect",
        "no number is correct", "all wrong", "all are incorrect", "none are correct",
        "no numbers correct", "nothing correct", "no digit is correct", "all digits incorrect"
    ]):
        return PuzzleClue(
            guess=guess,
            text=clue_text.strip(),
            total_correct=0,
            well_placed=0,
            wrong_placed=0,
            is_absent=True
        )

    # 2. Mixed: e.g. "Two numbers are correct, but only one is in the correct position"
    mixed_m = re.search(
        r"(one|two|three|four|1|2|3|4)\s+(?:numbers?|digits?)\s+(?:are|is)?\s*correct[,\s]+(?:but|and|yet)?\s*(?:only\s*)?(one|two|three|1|2|3)\s+(?:is|are)?\s*(?:in\s+the\s+correct\s+position|in\s+the\s+right\s+place|well\s*placed|correctly\s+placed|in\s+correct\s+place|in\s+correct\s+position)",
        clue_lower
    )
    if mixed_m:
        tc = WORD_TO_NUM.get(mixed_m.group(1), 0)
        wp = WORD_TO_NUM.get(mixed_m.group(2), 0)
        return PuzzleClue(
            guess=guess,
            text=clue_text.strip(),
            total_correct=tc,
            well_placed=wp,
            wrong_placed=max(0, tc - wp),
            is_absent=False
        )

    # 3. Wrong position(s): e.g. "Two numbers are correct, but both are in the wrong positions" or "One number is correct but wrongly placed"
    wrong_m = re.search(
        r"(one|two|three|four|1|2|3|4)\s+(?:numbers?|digits?)\s+(?:are|is)?\s*correct[,\s]+(?:but|and)?\s*(?:both|all)?\s*(?:are\s+)?(?:in\s+the\s+wrong\s+positions?|in\s+wrong\s+places?|wrongly\s*placed|wrong\s+positions?|wrong\s+places?|wrong\s+position|all\s+wrong\s+places?)",
        clue_lower
    )
    if wrong_m:
        tc = WORD_TO_NUM.get(wrong_m.group(1), 0)
        return PuzzleClue(
            guess=guess,
            text=clue_text.strip(),
            total_correct=tc,
            well_placed=0,
            wrong_placed=tc,
            is_absent=False
        )

    # 4. Well placed / Correct position only: e.g. "One number is correct and well placed"
    well_m = re.search(
        r"(one|two|three|four|1|2|3|4)\s+(?:numbers?|digits?)\s+(?:are|is)?\s*correct[,\s]+(?:and|but)?\s*(?:well\s*placed|in\s+the\s+correct\s+position|in\s+the\s+right\s+place|in\s+correct\s+place|in\s+correct\s+position|correctly\s+placed)",
        clue_lower
    )
    if well_m:
        tc = WORD_TO_NUM.get(well_m.group(1), 0)
        return PuzzleClue(
            guess=guess,
            text=clue_text.strip(),
            total_correct=tc,
            well_placed=tc,
            wrong_placed=0,
            is_absent=False
        )

    # 5. Short phrases: e.g. "1 correct & well placed", "1 correct & wrong place", "2 correct, wrong places"
    short_wp = re.search(r"(\d+)\s*correct\s*(?:&|and)?\s*(?:well\s*placed|right\s*place|correct\s*pos)", clue_lower)
    if short_wp:
        tc = int(short_wp.group(1))
        return PuzzleClue(guess=guess, text=clue_text.strip(), total_correct=tc, well_placed=tc, wrong_placed=0)

    short_wr = re.search(r"(\d+)\s*correct\s*(?:&|and|but)?\s*(?:wrong\s*place|wrong\s*pos|wrongly\s*placed)", clue_lower)
    if short_wr:
        tc = int(short_wr.group(1))
        return PuzzleClue(guess=guess, text=clue_text.strip(), total_correct=tc, well_placed=0, wrong_placed=tc)

    return None



def parse_clues_from_text(text: str) -> List[PuzzleClue]:
    """Extracts and parses all puzzle clues from multiline or single-line text."""
    clues: List[PuzzleClue] = []
    if not text:
        return clues

    # Split lines and also split multiple clues packed into a single line
    raw_lines: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Split on boundaries where a clue starts after a period or whitespace
        sub_chunks = re.split(r'(?<=[.!?;\n])\s*(?=[\[\(]?\s*\d{2,6}\s*[\]\)]?\s*[:\->–|—=→])', line)
        if len(sub_chunks) == 1:
            sub_chunks = re.split(r'(?<=\w)\s*\.\s*(?=[\[\(]?\s*\d{2,6}\s*[\]\)]?\s*[:\->–|—=→])', line)
        for chunk in sub_chunks:
            chunk = chunk.strip()
            if chunk:
                raw_lines.append(chunk)

    for line in raw_lines:
        clue = parse_single_clue_line(line)
        if clue:
            # Prevent duplicate clue rows
            if not any(c.guess == clue.guess and c.total_correct == clue.total_correct and c.well_placed == clue.well_placed for c in clues):
                clues.append(clue)
    return clues


def is_code_puzzle_text(text: str) -> bool:
    """Determines if the text or query represents a 'Guess the Code' / Mastermind puzzle."""
    if not text:
        return False
    lower = text.lower()
    keywords = ["correct", "position", "placed", "wrong", "incorrect", "code", "lock", "mastermind", "digits"]
    kw_count = sum(1 for kw in keywords if kw in lower)
    has_clues = len(parse_clues_from_text(text)) >= 2
    return has_clues or (kw_count >= 3 and bool(re.search(r"\b\d{3,5}\b", text)))


def check_candidate_against_clue(cand: str, clue: PuzzleClue) -> Tuple[bool, int, int]:
    """
    Evaluates candidate code against a single clue.
    Returns:
      (matches: bool, actual_total_correct: int, actual_well_placed: int)
    """
    # Calculate well placed (exact position match)
    wp = sum(1 for i in range(min(len(cand), len(clue.guess))) if cand[i] == clue.guess[i])

    # Calculate total correct (multiset intersection)
    tc = sum(min(cand.count(d), clue.guess.count(d)) for d in set(clue.guess))

    if clue.is_absent or clue.total_correct == 0:
        match = (tc == 0 and wp == 0)
    else:
        match = (tc == clue.total_correct and wp == clue.well_placed)

    return match, tc, wp


def find_conflicting_clues(clues: List[PuzzleClue], code_length: int) -> List[Tuple[PuzzleClue, PuzzleClue]]:
    """Identifies pairs of clues that logically contradict each other."""
    conflicts: List[Tuple[PuzzleClue, PuzzleClue]] = []
    total_space = 10 ** code_length
    for i in range(len(clues)):
        for j in range(i + 1, len(clues)):
            c1 = clues[i]
            c2 = clues[j]
            pair_has_sol = False
            for k in range(total_space):
                cand = f"{k:0{code_length}d}"
                m1, _, _ = check_candidate_against_clue(cand, c1)
                m2, _, _ = check_candidate_against_clue(cand, c2)
                if m1 and m2:
                    pair_has_sol = True
                    break
            if not pair_has_sol:
                conflicts.append((c1, c2))
    return conflicts


def solve_code_puzzle(
    clues: List[PuzzleClue],
    code_length: Optional[int] = None
) -> Dict[str, Any]:
    """
    Deterministic constraint solver for N-digit code puzzles.
    Enumerate all candidates 000..999 (or length N) and tests each against every clue constraint.
    """
    if not clues:
        return {"status": "no_clues"}

    if not code_length:
        lengths = [len(c.guess) for c in clues if c.guess]
        code_length = max(set(lengths), key=lengths.count) if lengths else 3

    total_space = 10 ** code_length
    valid_candidates_distinct: List[str] = []
    valid_candidates_all: List[str] = []

    for i in range(total_space):
        cand = f"{i:0{code_length}d}"
        cand_matches = True
        for clue in clues:
            match, _, _ = check_candidate_against_clue(cand, clue)
            if not match:
                cand_matches = False
                break
        if cand_matches:
            valid_candidates_all.append(cand)
            if len(set(cand)) == len(cand):
                valid_candidates_distinct.append(cand)

    # Distinct digits is the standard in almost all Mastermind / code lock puzzles
    solutions = valid_candidates_distinct if valid_candidates_distinct else valid_candidates_all

    if len(solutions) == 1:
        return {
            "status": "unique",
            "solution": solutions[0],
            "solutions": solutions,
            "code_length": code_length
        }
    elif len(solutions) > 1:
        return {
            "status": "multiple",
            "solutions": solutions,
            "code_length": code_length
        }
    else:
        conflicts = find_conflicting_clues(clues, code_length)
        return {
            "status": "contradiction",
            "conflicts": conflicts,
            "code_length": code_length
        }


def format_code_puzzle_solution(result: Dict[str, Any], clues: List[PuzzleClue]) -> str:
    """
    Formats the solution adhering to:
    1. Final answer first (e.g. '🔐 Code: 153')
    2. Short step-by-step verification
    3. Extracted clues so the user can verify
    """
    status = result.get("status")

    if status == "unique":
        sol = result["solution"]
        out = [f"🔐 **Code: {sol}**\n"]

        out.append("**Extracted Clues:**")
        for c in clues:
            out.append(f"• `{c.guess}` → {c.text}")
        out.append("")

        out.append("**Step-by-Step Verification:**")
        step_idx = 1
        for c in clues:
            _, tc, wp = check_candidate_against_clue(sol, c)
            present_digits = [d for d in c.guess if d in sol]
            if c.is_absent or c.total_correct == 0:
                out.append(f"{step_idx}. **`{c.guess}` (All incorrect):** Eliminates digits {', '.join(c.guess)}. None of these digits appear in `{sol}`.")
            elif wp > 0 and wp == tc:
                out.append(f"{step_idx}. **`{c.guess}` ({tc} correct & well placed):** Digit '{present_digits[0]}' is in `{sol}` at the exact matching position.")
            elif wp == 0:
                out.append(f"{step_idx}. **`{c.guess}` ({tc} correct, wrong positions):** Digits {', '.join(present_digits)} are present in `{sol}` but in different positions.")
            else:
                out.append(f"{step_idx}. **`{c.guess}` ({tc} correct, {wp} well placed):** Digits {', '.join(present_digits)} are present in `{sol}`, with {wp} in the correct position.")
            step_idx += 1

        out.append(f"\n✅ **Result:** `{sol}` is the unique code satisfying all {len(clues)} clues.")
        return "\n".join(out)

    elif status == "multiple":
        sols = result.get("solutions", [])
        sols_str = ", ".join(f"`{s}`" for s in sols[:8])
        if len(sols) > 8:
            sols_str += f" and {len(sols) - 8} more"

        out = [
            f"🔐 **Multiple Solutions Found ({len(sols)} possible codes):**\n",
            f"• **Valid Codes:** {sols_str}\n",
            "**Extracted Clues:**"
        ]
        for c in clues:
            out.append(f"• `{c.guess}` → {c.text}")
        out.append("\n⚠️ *The provided clues are consistent, but multiple solutions remain without additional constraints.*")
        return "\n".join(out)

    elif status == "contradiction":
        conflicts = result.get("conflicts", [])
        out = [
            "⚠️ **No Valid Solution (Logical Contradiction):**\n",
            "The clues provided in this puzzle conflict with one another and cannot be simultaneously satisfied.\n",
            "**Extracted Clues:**"
        ]
        for c in clues:
            out.append(f"• `{c.guess}` → {c.text}")

        if conflicts:
            out.append("\n**Identified Conflict:**")
            for c1, c2 in conflicts[:2]:
                out.append(f"• Clue `{c1.guess}` ({c1.text}) directly contradicts clue `{c2.guess}` ({c2.text}).")

        out.append("\nPlease check if any digit or clue wording in the image was transcribed incorrectly.")
        return "\n".join(out)

    return "⚠️ Could not solve this question. Please check the wording and try again."


def extract_ocr_text_multipass(image_path: str) -> str:
    """
    Robust multi-pass OCR preprocessing using Pillow and Tesseract:
    - Pass 1: Grayscale + high contrast
    - Pass 2: Binary thresholding
    - Pass 3: Inverted binary (for light text on dark background)
    - Pass 4: 2x upscaling for low-resolution images
    """
    try:
        import pytesseract
        img = Image.open(image_path)

        # Upscale if small image
        if img.width < 800 or img.height < 600:
            scale_factor = max(2, int(1000 / max(img.width, 1)))
            img = img.resize((img.width * scale_factor, img.height * scale_factor), Image.Resampling.LANCZOS)

        texts = []

        # Pass 1: Contrast enhanced grayscale
        gray = img.convert("L")
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(2.0)
        t1 = pytesseract.image_to_string(enhanced)
        if t1.strip():
            texts.append(t1.strip())

        # Pass 2: Binary thresholding
        threshold = 128
        bin_img = gray.point(lambda p: 255 if p > threshold else 0)
        t2 = pytesseract.image_to_string(bin_img)
        if t2.strip():
            texts.append(t2.strip())

        # Pass 3: Inverted binary (for light text on dark background)
        inv_img = ImageOps.invert(gray)
        t3 = pytesseract.image_to_string(inv_img)
        if t3.strip():
            texts.append(t3.strip())

        # Combine or select the text that yielded the most clues
        best_text = ""
        max_clues = -1
        for candidate_text in texts:
            clues = parse_clues_from_text(candidate_text)
            if len(clues) > max_clues:
                max_clues = len(clues)
                best_text = candidate_text

        return best_text if best_text else (texts[0] if texts else "")
    except Exception as e:
        logger.warning(f"Multipass OCR error: {e}")
        return ""


def select_solve_emoji(question_text: str, domain: Optional[str] = None) -> str:
    """Selects a contextually appropriate emoji based on question type / subject domain."""
    if not question_text:
        return "🎓"

    lower = question_text.lower()

    # Code / Lock / Mastermind
    if any(k in lower for k in ["code", "lock", "mastermind", "well placed", "wrong position", "guess the code", "digits are correct"]):
        return "🔐"

    # Logic / Puzzle / Riddle
    if any(k in lower for k in ["puzzle", "riddle", "logic", "reasoning", "brain teaser", "pattern", "sequence"]):
        return "🧩"

    # Multiple Choice Questions (MCQ) (Check before domain keywords to prioritize MCQ format)
    if re.search(r"\b[A-D]\)\s+[A-Za-z0-9]", question_text) or any(k in lower for k in ["mcq", "choose correct option", "choose the correct option", "choose the correct", "which of the following"]):
        return "🎯"

    # Mathematics
    if any(k in lower for k in ["derivative", "integral", "matrix", "calculus", "algebra", "equation", "geometry", "trigonometry", "sin(", "cos(", "tan(", "polynomial", "probability", "sqrt", "limit"]):
        return "📐"

    # Physics
    if any(k in lower for k in ["physics", "velocity", "acceleration", "force", "gravity", "thermodynamics", "quantum", "electric", "magnetic", "circuit", "ohm"]):
        return "⚡"

    # Chemistry
    if any(k in lower for k in ["chemistry", "reaction", "acid", "base", "ph", "molecule", "atomic", "molar", "stoichiometry", "catalyst"]):
        return "🧪"

    # Biology / Medicine
    if any(k in lower for k in ["biology", "cell", "dna", "rna", "organism", "genetics", "photosynthesis", "enzyme", "species"]):
        return "🧬"

    # Computer Science / Coding
    if any(k in lower for k in ["python", "java", "c++", "algorithm", "complexity", "big o", "sql", "array", "binary tree", "recursion", "function", "pointer"]):
        return "💻"

    # Economics / Stats
    if any(k in lower for k in ["inflation", "gdp", "supply", "demand", "microeconomics", "macroeconomics", "regression", "standard deviation", "variance"]):
        return "📊"

    # History / Humanities
    if any(k in lower for k in ["history", "war", "century", "dynasty", "treaty", "revolution", "constitution", "emperor"]):
        return "📜"

    return "🎓"


def solve_image_or_text_problem(
    query_text: str = "",
    image_path: Optional[str] = None,
    caption: Optional[str] = None
) -> str:
    """
    Unified Universal AI Problem Solver Pipeline:
    1. Resolves input (Image, Caption, or Text Query).
    2. If Image: runs multi-pass OCR + Vision multimodal extraction.
    3. If Guess the Code / Mastermind puzzle: extracts clues and runs exact constraint solver.
    4. If General Question (MCQ, Math, Physics, CS): solves via multimodal LLM tutor chain.
    5. Returns formatted answer with contextual emoji, final answer first, and clear explanation.
    """
    clean_query = (query_text or "").strip()
    clean_caption = (caption or "").strip()
    target_image = image_path.strip() if image_path else None

    # Handle case where clean_query contains an image URL or local file path
    if not target_image and clean_query:
        first_token = clean_query.split(maxsplit=1)[0].strip()
        if first_token.startswith(("http://", "https://")) or os.path.exists(first_token) or first_token.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            target_image = first_token
            clean_query = clean_query.split(maxsplit=1)[1].strip() if len(clean_query.split(maxsplit=1)) > 1 else ""

    if not target_image and not clean_query and not clean_caption:
        return "🎓 **Universal AI Problem Solver Usage:**\n• `/solve <question text>`\n• `/solve <image_url_or_file>`\n_Or send a photo of any math, physics, coding or exam question directly in chat!_"

    extracted_text = ""
    vision_transcription = ""

    # 1. Image Processing Pipeline
    if target_image:
        # Download image if URL
        if target_image.startswith(("http://", "https://")):
            try:
                os.makedirs("/tmp/alya_solver", exist_ok=True)
                local_f = f"/tmp/alya_solver/img_{int(time.time())}.png"
                r = requests.get(target_image, timeout=15)
                if r.status_code == 200:
                    with open(local_f, "wb") as f_out:
                        f_out.write(r.content)
                    target_image = local_f
            except Exception as e_dl:
                logger.warning(f"Could not download image {target_image}: {e_dl}")

        if os.path.exists(target_image):
            # Run local multi-pass OCR
            ocr_res = extract_ocr_text_multipass(target_image)
            if ocr_res:
                extracted_text = ocr_res

            # Try parsing code clues from OCR
            clues = parse_clues_from_text(extracted_text)
            if len(clues) >= 2:
                solve_res = solve_code_puzzle(clues)
                if solve_res.get("status") == "unique":
                    return format_code_puzzle_solution(solve_res, clues)

            # If OCR didn't yield a unique code puzzle solution, invoke Vision Multimodal LLM
            vision_prompt = (
                "You are an expert OCR, puzzle transcription, and academic visual reader. "
                "Carefully inspect this image:\n"
                "1. If this image is a 'Guess the Code' / Mastermind / Lock number puzzle: transcribe every single row and clue verbatim in this exact format:\n"
                "[DIGITS] -> [CLUE DESCRIPTION]\n"
                "Example:\n"
                "079 -> All numbers are incorrect\n"
                "165 -> Two numbers are correct, but only one is in the correct position\n"
                "359 -> Two numbers are correct, but only one is in the correct position\n"
                "365 -> Two numbers are correct, but both are in the wrong positions\n"
                "Keep all digits, positions, and wording 100% exact. Do not guess an answer.\n\n"
                "2. If this is a multiple-choice question (MCQ), math, physics, coding, or science problem: transcribe the question and choices verbatim, then solve it showing the Final Answer at the top with step-by-step reasoning."
            )
            if clean_caption:
                vision_prompt += f"\nUser Caption/Context: {clean_caption}"
            if clean_query:
                vision_prompt += f"\nUser Question: {clean_query}"

            v_res, v_prov = llm_provider.LLMProviderManager.call_vision_completion(
                image_path_or_url=target_image,
                prompt=vision_prompt,
                temperature=0.1,
                max_tokens=1000
            )
            if v_res:
                vision_transcription = v_res
                v_clues = parse_clues_from_text(vision_transcription)
                if len(v_clues) >= 2:
                    solve_res = solve_code_puzzle(v_clues)
                    if solve_res.get("status") == "unique":
                        return format_code_puzzle_solution(solve_res, v_clues)

                # If v_clues alone didn't yield unique solution, try combined
                combined_dict = {}
                for c in v_clues + clues:
                    combined_dict[c.guess] = c
                combined_clues = list(combined_dict.values())

                if len(combined_clues) >= 2:
                    solve_res = solve_code_puzzle(combined_clues)
                    return format_code_puzzle_solution(solve_res, combined_clues)


                # If vision solved a general question directly:
                emoji = select_solve_emoji(clean_query or clean_caption or vision_transcription)
                if not vision_transcription.startswith(emoji):
                    return f"{emoji} **AI Problem Solution:**\n\n{vision_transcription}"
                return vision_transcription


    # 2. Text-only / Fallback Question Solving Pipeline
    full_prompt_text = clean_query or clean_caption or extracted_text or vision_transcription
    if not full_prompt_text:
        return "⚠️ Could not solve this question. The image could not be clearly read and no text was provided."

    # Check if text itself is a code puzzle
    text_clues = parse_clues_from_text(full_prompt_text)
    if len(text_clues) >= 2:
        solve_res = solve_code_puzzle(text_clues)
        return format_code_puzzle_solution(solve_res, text_clues)

    # General Academic & MCQ Solver
    emoji = select_solve_emoji(full_prompt_text)
    system_prompt = (
        f"You are Alya's Master Problem Solving AI — an elite multi-discipline academic tutor and logic genius.\n"
        f"Formatting Rules:\n"
        f"1. Give the **Final Answer** clearly at the top (e.g. '**Final Answer:** [Option B / 42 / formula]').\n"
        f"2. 💡 **Step-by-Step Solution**: Show concise, complete logical derivations and proof.\n"
        f"3. 🧠 **Key Concept**: 1-line concept takeaway.\n"
        f"Tone: Direct, accurate, mathematically rigorous, using LaTeX/Unicode math where appropriate."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please solve this problem thoroughly:\n\n{full_prompt_text}"}
    ]

    try:
        solution, _, _ = llm_provider.LLMProviderManager.call_chat_completion(
            messages=messages,
            temperature=0.2,
            max_tokens=1000
        )
        if solution:
            return f"{emoji} **Solution:**\n\n{solution}"
    except Exception as e:
        logger.error(f"Error solving problem: {e}")

    return "⚠️ Could not solve this question. Please check the wording and try again."

