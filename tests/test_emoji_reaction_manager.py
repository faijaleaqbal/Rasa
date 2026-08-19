"""
Unit & Integration Test Suite for Alya's Context-Aware Emoji Reaction Manager.

Tests coverage:
1. Greetings ("Hi", "Hello", "Hey", "Namaste", "Good morning", "Hi buddy")
2. Thanks ("Thank you", "Thanks", "You're helpful", "Thank you bro")
3. Happiness & Excitement ("I'm happy", "That's amazing", "I got it", "Wow!", "I finally fixed my bot")
4. Love & Affection ("I love you", "You're cute", "Love you")
5. Sadness & Grief ("I'm sad", "I feel bad", "She left me", "I'm depressed", "I'm sad today", crying)
6. Anger & Frustration ("I'm angry", "This is annoying", "WTF", "This isn't working")
7. Confusion ("What?", "I don't understand", "How does this work?")
8. Questions ("What is Python?", informational inquiries, no auto ? spam)
9. Jokes & Humor ("LOL", "Haha", "That's funny", "😂😂 that's funny")
10. Surprise ("Really?", "No way!", "What happened?!")
11. Agreement / Confirmation ("Okay", "Yes", "Correct", "Got it")
12. Disagreement / Rejection ("No", "Wrong", "I don't want this")
13. Neutral messages (subtle or no reaction)
14. Context-dependent conversations (Celebration followed by venting about past struggle)
15. Emoji spam prevention (Input already emoji-heavy or long code snippet)
16. Non-randomness & determinism guarantee (same input always produces the exact same valid reaction)
17. Safety & Empathy rules (never laugh at sadness, no inappropriate emojis)
"""

import unittest
from addons.emoji_reaction_manager import (
    EmojiReactionManager,
    EmojiCategory,
    CATEGORY_EMOJIS,
    get_emoji_reaction_manager,
)


class TestEmojiReactionManager(unittest.TestCase):

    def setUp(self):
        self.manager = EmojiReactionManager()

    def test_greetings(self):
        # 1. Greetings: "Hi", "Hello", "Hey", "Namaste", "Good morning", "Hi buddy"
        greetings_pool = set(CATEGORY_EMOJIS[EmojiCategory.GREETINGS])
        
        rxn_hi_buddy = self.manager.get_reaction("Hi buddy")
        self.assertEqual(rxn_hi_buddy, "👋")
        self.assertIn(rxn_hi_buddy, greetings_pool)

        rxn_hello = self.manager.get_reaction("Hello")
        self.assertIn(rxn_hello, greetings_pool)

        rxn_hey = self.manager.get_reaction("Hey")
        self.assertIn(rxn_hey, greetings_pool)

        rxn_namaste = self.manager.get_reaction("Namaste")
        self.assertEqual(rxn_namaste, "🙏")
        self.assertIn(rxn_namaste, greetings_pool)

        rxn_morning = self.manager.get_reaction("Good morning")
        self.assertEqual(rxn_morning, "🌅")
        self.assertIn(rxn_morning, greetings_pool)

    def test_thanks(self):
        # 2. Thanks: "Thank you", "Thanks", "You're helpful", "Thank you bro"
        thanks_pool = set(CATEGORY_EMOJIS[EmojiCategory.THANKS])

        rxn_thanks_bro = self.manager.get_reaction("Thank you bro")
        self.assertEqual(rxn_thanks_bro, "🙏")
        self.assertIn(rxn_thanks_bro, thanks_pool)

        rxn_thanks = self.manager.get_reaction("Thanks")
        self.assertEqual(rxn_thanks, "🙏")
        self.assertIn(rxn_thanks, thanks_pool)

        rxn_helpful = self.manager.get_reaction("You're helpful")
        self.assertEqual(rxn_helpful, "😊")
        self.assertIn(rxn_helpful, thanks_pool)

        rxn_thank_you = self.manager.get_reaction("Thank you so much for the help")
        self.assertIn(rxn_thank_you, thanks_pool)

    def test_happiness_and_excitement(self):
        # 3. Happiness / Excitement: "I'm happy", "That's amazing", "I got it", "Wow!"
        happy_pool = set(CATEGORY_EMOJIS[EmojiCategory.HAPPINESS_EXCITEMENT])

        rxn_amazing = self.manager.get_reaction("That's amazing!")
        self.assertEqual(rxn_amazing, "🤩")
        self.assertIn(rxn_amazing, happy_pool)

        rxn_got_it = self.manager.get_reaction("I finally fixed my bot")
        self.assertEqual(rxn_got_it, "🎉")
        self.assertIn(rxn_got_it, happy_pool)

        rxn_happy = self.manager.get_reaction("I'm happy")
        self.assertEqual(rxn_happy, "😊")
        self.assertIn(rxn_happy, happy_pool)

        rxn_wow = self.manager.get_reaction("Wow!")
        self.assertEqual(rxn_wow, "🔥")
        self.assertIn(rxn_wow, happy_pool)

    def test_love_and_affection(self):
        # 4. Love / Affection: "I love you", "You're cute", "Love you"
        love_pool = set(CATEGORY_EMOJIS[EmojiCategory.LOVE_AFFECTION])

        rxn_love = self.manager.get_reaction("I love you")
        self.assertEqual(rxn_love, "❤️")
        self.assertIn(rxn_love, love_pool)

        rxn_cute = self.manager.get_reaction("You're cute")
        self.assertEqual(rxn_cute, "🥰")
        self.assertIn(rxn_cute, love_pool)

        rxn_love_u = self.manager.get_reaction("Love you")
        self.assertIn(rxn_love_u, love_pool)

    def test_sadness_and_grief(self):
        # 5. Sadness: "I'm sad", "I feel bad", "She left me", "I'm depressed", "I'm sad today"
        sad_pool = set(CATEGORY_EMOJIS[EmojiCategory.SADNESS])

        rxn_sad_today = self.manager.get_reaction("I'm sad today")
        self.assertEqual(rxn_sad_today, "😔")
        self.assertIn(rxn_sad_today, sad_pool)

        rxn_feel_bad = self.manager.get_reaction("I feel bad")
        self.assertEqual(rxn_feel_bad, "😔")
        self.assertIn(rxn_feel_bad, sad_pool)

        rxn_she_left = self.manager.get_reaction("She left me")
        self.assertEqual(rxn_she_left, "🫂")
        self.assertIn(rxn_she_left, sad_pool)

        rxn_depressed = self.manager.get_reaction("I'm depressed")
        self.assertEqual(rxn_depressed, "💙")
        self.assertIn(rxn_depressed, sad_pool)

        # Safety Guarantee: NEVER laughing emojis for sad messages
        forbidden_for_sadness = {"😂", "🤣", "😆", "🎉", "🔥", "🤡", "😜"}
        for sad_msg in ["I'm sad", "I feel bad", "She left me", "I'm depressed", "Crying so hard 😭"]:
            rxn = self.manager.get_reaction(sad_msg)
            self.assertNotIn(rxn, forbidden_for_sadness)
            self.assertIn(rxn, sad_pool)

    def test_anger_and_frustration(self):
        # 6. Anger / Frustration: "I'm angry", "This is annoying", "WTF", "This isn't working"
        anger_pool = set(CATEGORY_EMOJIS[EmojiCategory.ANGER_FRUSTRATION])

        rxn_angry = self.manager.get_reaction("I'm angry")
        self.assertEqual(rxn_angry, "😠")
        self.assertIn(rxn_angry, anger_pool)

        rxn_annoying = self.manager.get_reaction("This is annoying")
        self.assertEqual(rxn_annoying, "😤")
        self.assertIn(rxn_annoying, anger_pool)

        rxn_wtf = self.manager.get_reaction("WTF")
        self.assertEqual(rxn_wtf, "🤦")
        self.assertIn(rxn_wtf, anger_pool)

        rxn_not_working = self.manager.get_reaction("This isn't working")
        self.assertEqual(rxn_not_working, "🤦")
        self.assertIn(rxn_not_working, anger_pool)

    def test_confusion(self):
        # 7. Confusion: "What?", "I don't understand", "How does this work?"
        conf_pool = set(CATEGORY_EMOJIS[EmojiCategory.CONFUSION])

        rxn_what = self.manager.get_reaction("What?")
        self.assertEqual(rxn_what, "🤔")
        self.assertIn(rxn_what, conf_pool)

        rxn_dont_und = self.manager.get_reaction("I don't understand")
        self.assertEqual(rxn_dont_und, "😕")
        self.assertIn(rxn_dont_und, conf_pool)

        rxn_how = self.manager.get_reaction("How does this work?")
        self.assertEqual(rxn_how, "🤔")
        self.assertIn(rxn_how, conf_pool)

    def test_surprise(self):
        # 8. Surprise: "Really?", "No way!", "What happened?!"
        surp_pool = set(CATEGORY_EMOJIS[EmojiCategory.SURPRISE])

        rxn_really = self.manager.get_reaction("Really?")
        self.assertEqual(rxn_really, "😳")
        self.assertIn(rxn_really, surp_pool)

        rxn_no_way = self.manager.get_reaction("No way!")
        self.assertEqual(rxn_no_way, "🤯")
        self.assertIn(rxn_no_way, surp_pool)

        rxn_what_happened = self.manager.get_reaction("What happened?!")
        self.assertEqual(rxn_what_happened, "😮")
        self.assertIn(rxn_what_happened, surp_pool)

    def test_laughing_and_joke(self):
        # 9. Laughing / Joke: "LOL", "Haha", "That's funny", "😂😂 that's funny"
        joke_pool = set(CATEGORY_EMOJIS[EmojiCategory.LAUGHING_JOKE])

        rxn_lol = self.manager.get_reaction("LOL")
        self.assertEqual(rxn_lol, "😂")
        self.assertIn(rxn_lol, joke_pool)

        rxn_haha = self.manager.get_reaction("Haha")
        self.assertEqual(rxn_haha, "😂")
        self.assertIn(rxn_haha, joke_pool)

        rxn_funny = self.manager.get_reaction("That's funny")
        self.assertEqual(rxn_funny, "🤣")
        self.assertIn(rxn_funny, joke_pool)

        rxn_emoji_funny = self.manager.get_reaction("😂😂 that's funny")
        self.assertEqual(rxn_emoji_funny, "🤣")
        self.assertIn(rxn_emoji_funny, joke_pool)

    def test_agreement_and_confirmation(self):
        # 10. Agreement: "Okay", "Yes", "Correct", "Got it"
        agree_pool = set(CATEGORY_EMOJIS[EmojiCategory.AGREEMENT_CONFIRMATION])

        rxn_ok = self.manager.get_reaction("Okay")
        self.assertEqual(rxn_ok, "👍")
        self.assertIn(rxn_ok, agree_pool)

        rxn_yes = self.manager.get_reaction("Yes")
        self.assertEqual(rxn_yes, "👍")
        self.assertIn(rxn_yes, agree_pool)

        rxn_correct = self.manager.get_reaction("Correct")
        self.assertEqual(rxn_correct, "✅")
        self.assertIn(rxn_correct, agree_pool)

        rxn_got_it = self.manager.get_reaction("Got it")
        self.assertEqual(rxn_got_it, "👌")
        self.assertIn(rxn_got_it, agree_pool)

    def test_disagreement_and_rejection(self):
        # 11. Disagreement: "No", "Wrong", "I don't want this"
        disagree_pool = set(CATEGORY_EMOJIS[EmojiCategory.DISAGREEMENT_REJECTION])

        rxn_no = self.manager.get_reaction("No")
        self.assertEqual(rxn_no, "❌")
        self.assertIn(rxn_no, disagree_pool)

        rxn_wrong = self.manager.get_reaction("Wrong")
        self.assertEqual(rxn_wrong, "❌")
        self.assertIn(rxn_wrong, disagree_pool)

        rxn_dont_want = self.manager.get_reaction("I don't want this")
        self.assertEqual(rxn_dont_want, "👎")
        self.assertIn(rxn_dont_want, disagree_pool)

    def test_informational_questions(self):
        # 12. Question: "What is Python?", "How to make a tea"
        # Prefer: "🤔 💡", do NOT automatically use a question-mark emoji
        rxn_py = self.manager.get_reaction("What is Python?")
        self.assertEqual(rxn_py, "🤔")

        rxn_how_to = self.manager.get_reaction("How to calculate compound interest?")
        self.assertIn(rxn_how_to, ["🤔", "💡"])

    def test_neutral_messages(self):
        # 13. Neutral Messages: subtle or None
        rxn_short_neutral = self.manager.get_reaction("Table has 4 columns.")
        self.assertIn(rxn_short_neutral, ["🙂", None])

        rxn_factual = self.manager.get_reaction("The meeting is scheduled at 4 PM in room 302.")
        self.assertIn(rxn_factual, ["🙂", None])

    def test_context_dependent_flow(self):
        # 14. Context Awareness:
        # User: "I finally fixed my bot" -> Reaction: "🎉"
        # Alya: "That's great!"
        # Then user: "It was broken for 3 days 😭" -> Reaction understands context (sympathetic relief / support)
        user_id = "test_user_context_999"
        self.manager.clear_context(user_id)

        # Turn 1:
        rxn1 = self.manager.get_reaction("I finally fixed my bot", user_id=user_id)
        self.assertEqual(rxn1, "🎉")

        # Bot response in between:
        self.manager.record_turn(user_id, role="assistant", text="That's great!")

        # Turn 2:
        analysis = self.manager.analyze_message("It was broken for 3 days 😭", user_id=user_id)
        self.assertTrue(analysis.context_adjusted)
        self.assertEqual(analysis.selected_emoji, "🫂")

    def test_emoji_spam_prevention(self):
        # 15. Spam Prevention:
        # A. Already emoji-heavy user message
        emoji_heavy_msg = "Hey check this out! 🔥🎉🥳✨🚀💯"
        analysis = self.manager.analyze_message(emoji_heavy_msg)
        self.assertFalse(analysis.should_react)
        self.assertIsNone(self.manager.get_reaction(emoji_heavy_msg))

        # B. Long technical code snippet
        code_msg = (
            "```python\n"
            "def calculate_total(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        total += item['price'] * item['quantity']\n"
            "    return total\n"
            "```\n"
            "Please review this code implementation for tax calculation in India."
        )
        code_analysis = self.manager.analyze_message(code_msg)
        self.assertFalse(code_analysis.should_react)
        self.assertIsNone(self.manager.get_reaction(code_msg))

    def test_strict_determinism_and_no_randomness(self):
        # 16. Verify that the same message produces the exact same logically appropriate emoji every time
        test_phrases = [
            ("Hi buddy", "👋"),
            ("Thank you bro", "🙏"),
            ("That's amazing!", "🤩"),
            ("I'm sad today", "😔"),
            ("What is Python?", "🤔"),
            ("😂😂 that's funny", "🤣"),
        ]

        for phrase, expected_emoji in test_phrases:
            for _ in range(25):  # Run multiple times to guarantee no randomness
                rxn = self.manager.get_reaction(phrase)
                self.assertEqual(rxn, expected_emoji, f"Failed deterministic check on '{phrase}'")

    def test_fallback_mapping_by_category(self):
        # Verify fallback emojis are category-appropriate
        self.assertEqual(self.manager.get_fallback_emoji("🤩"), "🎉")
        self.assertEqual(self.manager.get_fallback_emoji("🙏"), "🙏")
        self.assertEqual(self.manager.get_fallback_emoji("😔"), "😢")
        self.assertEqual(self.manager.get_fallback_emoji(EmojiCategory.GREETINGS), "👍")


if __name__ == "__main__":
    unittest.main()
