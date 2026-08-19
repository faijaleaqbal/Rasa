"""
Comprehensive Regression Test Suite for /solve and Puzzle Solver.

Covers:
1. Text-only /solve
2. Image-only /solve
3. Image + caption /solve
4. Clear screenshot puzzle
5. Low-resolution screenshot puzzle
6. Multiple-choice question image / text
7. 3-digit code puzzle (079, 165, 359, 365 -> 153 and classic 042)
8. Contradictory puzzle (detects conflict)
9. Puzzle with multiple valid answers
10. Context-aware emoji behavior
11. Error handling for unreadable images / empty inputs
"""

import os
import unittest
from unittest.mock import patch
import tempfile
from PIL import Image, ImageDraw, ImageFont

from actions import puzzle_solver
from actions import skills_super_pack as superpack
from actions import commands


class TestPuzzleSolver(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.user_id = "test_user_solver_123"
        self.chat_id = "test_chat_solver_123"

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _get_font(self, size: int = 16):
        for font_path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
        ]:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    pass
        return None

    def _create_puzzle_image(self, clues_text: list, filename: str = "puzzle.png", size=(600, 300), low_res=False) -> str:
        """Helper to dynamically generate test puzzle images."""
        font = self._get_font(16)
        img = Image.new("RGB", size, color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        y = 20
        for line in clues_text:
            draw.text((20, y), line, fill=(0, 0, 0), font=font)
            y += int(size[1] / (len(clues_text) + 1))

        out_path = os.path.join(self.temp_dir, filename)
        if low_res:
            small_img = img.resize((300, 150), Image.Resampling.BILINEAR)
            small_img.save(out_path)
        else:
            img.save(out_path)
        return out_path

    def _create_mcq_image(self, question: str, options: list, filename: str = "mcq.png") -> str:
        """Helper to create MCQ test images."""
        font = self._get_font(16)
        img = Image.new("RGB", (700, 300), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), question, fill=(0, 0, 0), font=font)
        y = 70
        for opt in options:
            draw.text((40, y), opt, fill=(0, 0, 0), font=font)
            y += 45
        out_path = os.path.join(self.temp_dir, filename)
        img.save(out_path)
        return out_path


    # -----------------------------------------------------------------------
    # 1. 3-Digit Code Puzzle & Constraint Solving
    # -----------------------------------------------------------------------
    def test_3_digit_code_puzzle_user_example(self):
        """
        User's exact example:
        - 079 → All numbers are incorrect.
        - 165 → Two numbers are correct, but only one is in the correct position.
        - 359 → Two numbers are correct, but only one is in the correct position.
        - 365 → Two numbers are correct, but both are in the wrong positions.
        Solution: 153
        """
        puzzle_text = (
            "079 → All numbers are incorrect.\n"
            "165 → Two numbers are correct, but only one is in the correct position.\n"
            "359 → Two numbers are correct, but only one is in the correct position.\n"
            "365 → Two numbers are correct, but both are in the wrong positions."
        )
        clues = puzzle_solver.parse_clues_from_text(puzzle_text)
        self.assertEqual(len(clues), 4)

        result = puzzle_solver.solve_code_puzzle(clues)
        self.assertEqual(result["status"], "unique")
        self.assertEqual(result["solution"], "153")

        formatted = puzzle_solver.format_code_puzzle_solution(result, clues)
        self.assertIn("153", formatted)
        self.assertIn("079", formatted)
        self.assertIn("165", formatted)
        self.assertIn("359", formatted)
        self.assertIn("365", formatted)
        self.assertTrue(formatted.startswith("🔐 **Code: 153**"))

    def test_3_digit_code_puzzle_classic_042(self):
        """
        Classic Mastermind 042 puzzle:
        682 - One number is correct and well placed
        614 - One number is correct but wrongly placed
        206 - Two numbers are correct but wrongly placed
        738 - Nothing is correct
        780 - One number is correct but wrongly placed
        Solution: 042
        """
        puzzle_text = (
            "682 - One number is correct and well placed\n"
            "614 - One number is correct but wrongly placed\n"
            "206 - Two numbers are correct but wrongly placed\n"
            "738 - Nothing is correct\n"
            "780 - One number is correct but wrongly placed"
        )
        clues = puzzle_solver.parse_clues_from_text(puzzle_text)
        self.assertEqual(len(clues), 5)

        result = puzzle_solver.solve_code_puzzle(clues)
        self.assertEqual(result["status"], "unique")
        self.assertEqual(result["solution"], "042")

    # -----------------------------------------------------------------------
    # 2. Text-only /solve
    # -----------------------------------------------------------------------
    def test_text_only_solve_code_puzzle(self):
        """Testing /solve with code puzzle text directly."""
        cmd_text = (
            "/solve 079 → All numbers are incorrect. "
            "165 → Two numbers are correct, but only one is in the correct position. "
            "359 → Two numbers are correct, but only one is in the correct position. "
            "365 → Two numbers are correct, but both are in the wrong positions."
        )
        res = commands.handle_slash_command(cmd_text, self.user_id, self.chat_id)
        self.assertTrue(res.get("handled"))
        self.assertIn("153", res.get("text", ""))
        self.assertIn("🔐", res.get("text", ""))

    @patch("actions.llm_provider.LLMProviderManager.call_chat_completion")
    def test_text_only_solve_math_question(self, mock_llm):
        """Testing /solve with text math problem."""
        mock_llm.return_value = ("The derivative of x^3 is 3x^2.", None, "MockProvider")
        res = commands.handle_slash_command("/solve What is the derivative of x^3?", self.user_id, self.chat_id)
        self.assertTrue(res.get("handled"))
        self.assertIn("3x", res.get("text", ""))

    # -----------------------------------------------------------------------
    # 3. Image-only /solve
    # -----------------------------------------------------------------------
    def test_image_only_solve(self):
        """Testing /solve with attachment_path pointing to a code puzzle image."""
        img_path = self._create_puzzle_image([
            "079 - All numbers are incorrect",
            "165 - Two numbers are correct, but only one is in the correct position",
            "359 - Two numbers are correct, but only one is in the correct position",
            "365 - Two numbers are correct, but both are in the wrong positions"
        ], filename="test_img_only.png")

        res = commands.handle_slash_command("/solve", self.user_id, self.chat_id, attachment_path=img_path)
        self.assertTrue(res.get("handled"))
        self.assertIn("153", res.get("text", ""))

    # -----------------------------------------------------------------------
    # 4. Image + Caption /solve
    # -----------------------------------------------------------------------
    def test_image_with_caption_solve(self):
        """Testing /solve with both attachment_path and caption text."""
        img_path = self._create_puzzle_image([
            "079 - All numbers are incorrect",
            "165 - Two numbers are correct, but only one is in the correct position",
            "359 - Two numbers are correct, but only one is in the correct position",
            "365 - Two numbers are correct, but both are in the wrong positions"
        ], filename="test_img_caption.png")

        res = commands.handle_slash_command("/solve Please crack this 3-digit lock code", self.user_id, self.chat_id, attachment_path=img_path)
        self.assertTrue(res.get("handled"))
        self.assertIn("153", res.get("text", ""))

    def test_image_url_or_path_in_args_solve(self):
        """Testing /solve <path_to_image> with optional query in command line."""
        img_path = self._create_puzzle_image([
            "079 - All numbers are incorrect",
            "165 - Two numbers are correct, but only one is in the correct position",
            "359 - Two numbers are correct, but only one is in the correct position",
            "365 - Two numbers are correct, but both are in the wrong positions"
        ], filename="test_args_path.png")

        res = commands.handle_slash_command(f"/solve {img_path} find the code", self.user_id, self.chat_id)
        self.assertTrue(res.get("handled"))
        self.assertIn("153", res.get("text", ""))

    # -----------------------------------------------------------------------
    # 5. Clear Screenshot vs Low-Resolution Screenshot
    # -----------------------------------------------------------------------
    def test_clear_screenshot_solve(self):
        """Testing clear high-resolution puzzle image."""
        img_path = self._create_puzzle_image([
            "079 - All numbers are incorrect",
            "165 - Two numbers are correct, but only one is in the correct position",
            "359 - Two numbers are correct, but only one is in the correct position",
            "365 - Two numbers are correct, but both are in the wrong positions"
        ], filename="clear_screenshot.png", size=(800, 400), low_res=False)

        res = superpack.solve_question_or_problem(image_path=img_path)
        self.assertIn("153", res)

    @patch("actions.llm_provider.LLMProviderManager.call_vision_completion")
    def test_low_resolution_screenshot_solve(self, mock_vis):
        """Testing low-resolution / compressed image."""
        mock_vis.return_value = ("The lock code is 153.", "MockVision")
        img_path = self._create_puzzle_image([
            "079 - All numbers are incorrect",
            "165 - Two numbers are correct, but only one is in the correct position",
            "359 - Two numbers are correct, but only one is in the correct position",
            "365 - Two numbers are correct, but both are in the wrong positions"
        ], filename="low_res_screenshot.png", size=(400, 200), low_res=True)

        res = superpack.solve_question_or_problem(image_path=img_path)
        self.assertIn("153", res)

    # -----------------------------------------------------------------------
    # 6. Multiple Choice Image
    # -----------------------------------------------------------------------
    @patch("actions.llm_provider.LLMProviderManager.call_chat_completion")
    @patch("actions.llm_provider.LLMProviderManager.call_vision_completion")
    def test_multiple_choice_image_solve(self, mock_vis, mock_llm):
        """Testing multiple-choice question image."""
        mock_llm.return_value = ("The chemical symbol for Gold is Au (Option B).", None, "MockProvider")
        mock_vis.return_value = ("The chemical symbol for Gold is Au (Option B).", "MockVision")
        img_path = self._create_mcq_image(
            question="What is the chemical symbol for Gold?",
            options=["A) Ag", "B) Au", "C) Fe", "D) Cu"],
            filename="mcq_gold.png"
        )
        res = superpack.solve_question_or_problem(image_path=img_path)
        self.assertIn("Au", res)

    # -----------------------------------------------------------------------
    # 7. Contradictory Puzzle (Detects Inconsistency)
    # -----------------------------------------------------------------------
    def test_contradictory_puzzle(self):
        """
        Contradictory clues:
        079 - All numbers are incorrect (0, 7, 9 absent)
        079 - One number is correct and well placed (requires 0, 7, or 9 in code)
        """
        clues = [
            puzzle_solver.PuzzleClue(guess="079", text="All numbers are incorrect", total_correct=0, well_placed=0, is_absent=True),
            puzzle_solver.PuzzleClue(guess="079", text="One number is correct and well placed", total_correct=1, well_placed=1)
        ]
        result = puzzle_solver.solve_code_puzzle(clues, code_length=3)
        self.assertEqual(result["status"], "contradiction")

        formatted = puzzle_solver.format_code_puzzle_solution(result, clues)
        self.assertIn("Contradiction", formatted)
        self.assertIn("No Valid Solution", formatted)

    # -----------------------------------------------------------------------
    # 8. Puzzle with Multiple Valid Answers
    # -----------------------------------------------------------------------
    def test_multiple_valid_answers_puzzle(self):
        """
        Ambiguous clues (not enough constraints to yield a single 3-digit number).
        """
        clues = [
            puzzle_solver.PuzzleClue(guess="079", text="All numbers are incorrect", total_correct=0, well_placed=0, is_absent=True),
            puzzle_solver.PuzzleClue(guess="165", text="One number is correct and well placed", total_correct=1, well_placed=1)
        ]
        result = puzzle_solver.solve_code_puzzle(clues, code_length=3)
        self.assertEqual(result["status"], "multiple")
        self.assertGreater(len(result["solutions"]), 1)

        formatted = puzzle_solver.format_code_puzzle_solution(result, clues)
        self.assertIn("Multiple Solutions Found", formatted)

    # -----------------------------------------------------------------------
    # 9. Context-Aware Emoji Behavior
    # -----------------------------------------------------------------------
    def test_context_aware_emojis(self):
        """Verifies emojis are chosen contextually based on subject/domain."""
        self.assertEqual(puzzle_solver.select_solve_emoji("Guess the 3-digit lock code"), "🔐")
        self.assertEqual(puzzle_solver.select_solve_emoji("Solve this riddle and logic puzzle"), "🧩")
        self.assertEqual(puzzle_solver.select_solve_emoji("Find derivative of x^2 * sin(x)"), "📐")
        self.assertEqual(puzzle_solver.select_solve_emoji("Calculate electric force using Coulomb's law"), "⚡")
        self.assertEqual(puzzle_solver.select_solve_emoji("Balance this chemical reaction HCl + NaOH"), "🧪")
        self.assertEqual(puzzle_solver.select_solve_emoji("What is the function of DNA polymerase?"), "🧬")
        self.assertEqual(puzzle_solver.select_solve_emoji("Write a Python binary search function"), "💻")
        self.assertEqual(puzzle_solver.select_solve_emoji("Choose correct option: A) Newton B) Einstein"), "🎯")

    # -----------------------------------------------------------------------
    # 10. Empty Input / Error Handling
    # -----------------------------------------------------------------------
    def test_empty_input_handling(self):
        """Verifies usage guidance when no input or image is provided."""
        res = commands.handle_slash_command("/solve", "empty_user", "empty_chat")
        self.assertTrue(res.get("handled"))
        self.assertIn("Usage:", res.get("text", ""))


if __name__ == "__main__":
    unittest.main()
