"""
Context-Aware Emoji Reaction Manager for Alya.

Provides deterministic, intent- and emotion-driven emoji reaction selection
based on:
1. User message meaning, keywords, and emotion/sentiment.
2. Intent classification (English, Hindi, and Hinglish).
3. Short-term conversation context and history.
4. Emoji frequency / spam prevention rules.
5. Strict safety & empathy rules (e.g. supportive reactions for sadness, no random global emojis).
"""

import os
import re
import math
import time
import logging
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Tuple, Any, Deque

logger = logging.getLogger(__name__)


class EmojiCategory(str, Enum):
    GREETINGS = "greetings"
    HAPPINESS_EXCITEMENT = "happiness_excitement"
    LOVE_AFFECTION = "love_affection"
    THANKS = "thanks"
    SADNESS = "sadness"
    ANGER_FRUSTRATION = "anger_frustration"
    CONFUSION = "confusion"
    SURPRISE = "surprise"
    LAUGHING_JOKE = "laughing_joke"
    AGREEMENT_CONFIRMATION = "agreement_confirmation"
    DISAGREEMENT_REJECTION = "disagreement_rejection"
    QUESTION = "question"
    NEUTRAL = "neutral"


# Mappings of Category to valid, curated emojis
CATEGORY_EMOJIS: Dict[EmojiCategory, List[str]] = {
    EmojiCategory.GREETINGS: ["👋", "😊", "🙏", "🌅"],
    EmojiCategory.HAPPINESS_EXCITEMENT: ["😊", "😄", "🤩", "🎉", "🔥"],
    EmojiCategory.LOVE_AFFECTION: ["❤️", "🥰", "😘", "💕"],
    EmojiCategory.THANKS: ["🙏", "😊", "❤️"],
    EmojiCategory.SADNESS: ["😔", "😢", "🫂", "💙"],
    EmojiCategory.ANGER_FRUSTRATION: ["😤", "😠", "🤦"],
    EmojiCategory.CONFUSION: ["🤔", "😕", "❓"],
    EmojiCategory.SURPRISE: ["😳", "😮", "🤯"],
    EmojiCategory.LAUGHING_JOKE: ["😂", "🤣", "😆"],
    EmojiCategory.AGREEMENT_CONFIRMATION: ["👍", "✅", "👌"],
    EmojiCategory.DISAGREEMENT_REJECTION: ["❌", "👎", "😐"],
    EmojiCategory.QUESTION: ["🤔", "💡"],
    EmojiCategory.NEUTRAL: ["🙂"],
}

# Category fallbacks if Telegram Bot API rejects a specific emoji (e.g., custom emoji not supported)
CATEGORY_TELEGRAM_FALLBACKS: Dict[EmojiCategory, List[str]] = {
    EmojiCategory.GREETINGS: ["👍", "😊", "🙏", "❤️"],
    EmojiCategory.HAPPINESS_EXCITEMENT: ["🎉", "🔥", "🤩", "👍", "😁"],
    EmojiCategory.LOVE_AFFECTION: ["❤️", "🥰", "😘", "😍"],
    EmojiCategory.THANKS: ["🙏", "❤️", "👍", "👏"],
    EmojiCategory.SADNESS: ["😢", "😭", "💔", "😐"],
    EmojiCategory.ANGER_FRUSTRATION: ["😡", "🤬", "😐", "👎"],
    EmojiCategory.CONFUSION: ["🤔", "🤨", "🤷", "😐"],
    EmojiCategory.SURPRISE: ["🤯", "😱", "😮", "🔥"],
    EmojiCategory.LAUGHING_JOKE: ["🤣", "😂", "😁"],
    EmojiCategory.AGREEMENT_CONFIRMATION: ["👍", "👌", "👏", "🫡"],
    EmojiCategory.DISAGREEMENT_REJECTION: ["👎", "😐", "💔"],
    EmojiCategory.QUESTION: ["🤔", "🤓", "💡", "🫡"],
    EmojiCategory.NEUTRAL: ["👍", "😐"],
}

# Regex to detect raw unicode emojis in user text
EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50\u2b55\u200d\ufe0f]",
    flags=re.UNICODE,
)


@dataclass
class ConversationTurn:
    role: str  # "user" or "assistant"
    sanitized_text: str
    category: Optional[EmojiCategory] = None
    emoji_used: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReactionAnalysis:
    category: EmojiCategory
    confidence: float
    selected_emoji: Optional[str]
    should_react: bool
    reason: str
    context_adjusted: bool = False


class EmojiReactionManager:
    """
    Deterministic & Context-Aware Emoji Reaction Manager for Alya.
    Analyzes intent, sentiment, conversation history, and spam probability.
    """

    def __init__(self, max_context_turns: int = 6):
        self.max_context_turns = max_context_turns
        self._user_context: Dict[str, Deque[ConversationTurn]] = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compiles regex patterns for English, Hindi, and Hinglish emotion detection."""
        
        # 1. Greetings
        self.re_morning = re.compile(
            r"\b(good\s*morning|gm|suprabhat|shubh\s*prabhat|morning\s*bhai|morning\s*bro|morning\s*alya)\b",
            re.IGNORECASE,
        )
        self.re_namaste = re.compile(
            r"\b(namaste|namaskar|pranam|pranaam|radhe\s*radhe|jai\s*shree\s*ram|sat\s*sri\s*akaal|adaab|vanakkam)\b",
            re.IGNORECASE,
        )
        self.re_greeting = re.compile(
            r"\b(hi|hello|hey|hiya|yo|sup|kaisa\s*hai|kaise\s*ho|kya\s*haal|kem\s*cho|hi\s*buddy|hello\s*there|"
            r"hey\s*bro|hey\s*alya|heyy+|hiii+|helllo+|whats\s*up|what\'s\s*up|wassup|holla|greetings|salaam)\b",
            re.IGNORECASE,
        )

        # 2. Thanks / Gratitude
        self.re_thanks_bro = re.compile(
            r"\b(thank\s*you\s*(bro|bhai|buddy|dost|yaar|alya)|thanks\s*(bro|bhai|buddy|dost|yaar|alya))\b",
            re.IGNORECASE,
        )
        self.re_thanks = re.compile(
            r"\b(thank\s*you|thanks|thank\s*u|thx|ty|thankyou|shukriya|dhanyawad|dhanyavaad|many\s*thanks|"
            r"thanks\s*a\s*lot|you\'re\s*helpful|you\s*are\s*helpful|helpful|appreciate\s*it|much\s*appreciated|"
            r"grateful|bohot\s*shukriya|mehrbani|thanks\s*for\s*the\s*help)\b",
            re.IGNORECASE,
        )

        # 3. Love / Affection
        self.re_love = re.compile(
            r"\b(i\s*love\s*you|love\s*you|love\s*u|luv\s*u|you\'re\s*cute|you\s*are\s*cute|so\s*sweet|\bcute\b|"
            r"adorable|marry\s*me|kiss\s*you|muah|pyaar|pyar|dil\s*jeet\s*liya|sweetheart|ily|ily2|"
            r"i\s*love\s*alya|love\s*alya|meri\s*jaan|dil\s*aa\s*gaya)\b",
            re.IGNORECASE,
        )

        # 4. Sadness / Grief / Empathy (Strictly negative, no laughter)
        self.re_sadness_today = re.compile(
            r"\b(i\'?m\s*sad\s*today|i\s*am\s*sad\s*today|feeling\s*sad\s*today|sad\s*today)\b",
            re.IGNORECASE,
        )
        self.re_sadness = re.compile(
            r"\b(i\'?m\s*sad|i\s*am\s*sad|sad|unhappy|depressed|depression|crying|cry|cried|tears|"
            r"feel\s*bad|feeling\s*bad|feeling\s*low|feeling\s*down|heartbroken|broke\s*up|breakup|"
            r"she\s*left\s*me|he\s*left\s*me|lost\s*my\s*job|failed|died|passed\s*away|rip|grief|pain|"
            r"lonely|alone|nobody\s*loves\s*me|dukhi|mood\s*off|mood\s*kharab|dukhi\s*hu|bohot\s*sad|"
            r"pareshan\s*hu|rona\s*aa\s*raha|bura\s*din|horrible\s*day|worst\s*day|miss\s*her|miss\s*him|"
            r"miss\s*them|hopeless|terrible|disappointed|dil\s*toot\s*gaya|dard)\b",
            re.IGNORECASE,
        )

        # 5. Happiness / Excitement / Celebration
        self.re_amazing = re.compile(
            r"\b(that\'?s\s*amazing|that\s*is\s*amazing|amazing|mind\s*blowing|unbelievable\s*bro|"
            r"so\s*amazing|wow\s*amazing|that\'?s\s*awesome|awesome)\b",
            re.IGNORECASE,
        )
        self.re_fixed_it = re.compile(
            r"\b(i\s*finally\s*fixed|finally\s*fixed|fixed\s*it|fixed\s*my\s*bot|i\s*got\s*it|got\s*it\s*working|"
            r"solved\s*it|cracked\s*it|passed\s*the\s*exam|got\s*the\s*job|we\s*won|i\s*won)\b",
            re.IGNORECASE,
        )
        self.re_happiness = re.compile(
            r"\b(i\'?m\s*happy|i\s*am\s*happy|happy|excited|super\s*stoked|fantastic|wonderful|yay|hurray|"
            r"yesss|woohoo|wow|congrats|celebrate|celebration|bohot\s*badhiya|maza\s*aa\s*gaya|\bmast\b|zabardast|"
            r"ekdum\s*badhiya|first\s*class|party|winner|achievement|success|lets\s*go|let\'?s\s*go|fire|"
            r"khush\s*hu|mubaarak|badiya\s*hai)\b",
            re.IGNORECASE,
        )

        # 6. Anger / Frustration
        self.re_anger = re.compile(
            r"\b(i\'?m\s*angry|i\s*am\s*angry|angry|mad|annoyed|annoying|this\s*is\s*annoying|frustrated|"
            r"frustrating|pissed|pissed\s*off|irritated|furious|wtf|wth|what\s*the\s*hell|what\s*the\s*fuck|"
            r"fuck|shit|bullshit|this\s*sucks|this\s*isn\'?t\s*working|not\s*working|useless|stupid\s*bug|"
            r"hate\s*this|buggy|gussa|dimag\s*kharab|bakwas|bekaar|faltu|ghatiya|so\s*annoyed)\b",
            re.IGNORECASE,
        )

        # 7. Laughing / Joke / Humor
        self.re_funny_joke = re.compile(
            r"\b(that\'?s\s*funny|that\s*is\s*funny|funny|hilarious|lol|lmao|rofl|lmfao|haha+|hehe+|"
            r"joke|meme|hasna|hasi\s*aa\s*gayi|mazaak|chutkula|kya\s*joke\s*hai)\b",
            re.IGNORECASE,
        )

        # 8. Confusion / Doubt
        self.re_confusion = re.compile(
            r"(^what\s*[?!]+|^what\s+do\s+you\s+mean|i\s+don\'?t\s+understand|dont\s+understand|didn\'?t\s+get\s+it|"
            r"how\s+does\s+this\s+work|\bconfused\b|\bconfusing\b|makes\s+no\s+sense|^huh\s*[?!]+|^kya\s*[?!]+|kya\s+matlab|"
            r"samajh\s+nahi\s+aaya|samajh\s+nahi\s+aa\s+raha|meaning\s*[?!]+|explain\s+please|what\s+does\s+that\s+mean|"
            r"i\s+am\s+confused|^what\s+is\s+this\s*[?!]+|lost\s+me)",
            re.IGNORECASE,
        )

        # 9. Surprise / Shock
        self.re_surprise = re.compile(
            r"(really\s*[?!]+|no\s*way\s*[?!]*|what\s*happened\s*[?!]+|are\s*you\s*serious\s*[?!]*|"
            r"are\s*you\s*kidding\s*[?!]*|for\s*real\s*[?!]*|\bomg\b|oh\s*my\s*god|unbelievable|mind\s*blown|whoa|woah|"
            r"shocking|sach\s*me\s*[?!]+|kya\s*sach\s*me\s*[?!]+|are\s*you\s*sure\s*[?!]+)",
            re.IGNORECASE,
        )

        # 10. Agreement / Confirmation
        self.re_agreement = re.compile(
            r"^(okay|ok|okies|k|yes|yeah|yep|yup|correct|got\s*it|understood|makes\s*sense|agreed|agree|"
            r"sure|alright|all\s*right|perfect|done|sounds\s*good|fine|haan|haanji|theek\s*hai|sahi\s*hai|"
            r"bilkul|pakka|sahi\s*bola|cool|roger\s*that)[\.!\s]*$",
            re.IGNORECASE,
        )
        self.re_agreement_loose = re.compile(
            r"\b(okay|ok|yes|correct|got\s*it|makes\s*sense|agreed|alright|theek\s*hai|sahi\s*hai|bilkul)\b",
            re.IGNORECASE,
        )

        # 11. Disagreement / Rejection
        self.re_disagreement = re.compile(
            r"^(no|nope|nah|wrong|incorrect|i\s*don\'?t\s*want\s*this|dont\s*want\s*this|disagree|"
            r"not\s*really|never|cancel|stop|nahi|na|galat|bilkul\s*nahi|aisa\s*nahi\s*hai|nahi\s*chahiye)[\.!\s]*$",
            re.IGNORECASE,
        )
        self.re_disagreement_loose = re.compile(
            r"\b(no|nope|wrong|incorrect|i\s*don\'?t\s*want\s*this|dont\s*want\s*this|disagree|galat|nahi\s*chahiye)\b",
            re.IGNORECASE,
        )

        # 12. Question
        self.re_question_start = re.compile(
            r"^(what\s+is|what\s+are|what\s+was|how\s+to|how\s+do|how\s+does|why\s+is|why\s+does|where\s+is|"
            r"where\s+can|when\s+is|when\s+did|who\s+is|who\s+was|which\s+is|can\s+you\s+explain|tell\s+me\s+about|"
            r"explain\s+|kya\s+hota\s+hai|kaise\s+karein|kyun\s+hota\s+hai)",
            re.IGNORECASE,
        )

        # 13. Technical indicators for spam avoidance on long technical texts
        self.re_technical = re.compile(
            r"(```|def\s+\w+|import\s+\w+|from\s+\w+\s+import|class\s+\w+|SELECT\s+.*\s+FROM|"
            r"<script|<html|function\(|const\s+\w+\s*=|var\s+\w+\s*=|let\s+\w+\s*=|\{\s*\"|\{\s*\'|"
            r"Traceback\s+\(most\s+recent\s+call\s+last\)|Exception:\s+|Error:\s+|https?://\S+)",
            re.IGNORECASE,
        )

    def sanitize_for_context(self, text: str) -> str:
        """Sanitizes text before storing in memory context to avoid storing PII/sensitive tokens."""
        if not text:
            return ""
        # Remove emails
        cleaned = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", "[EMAIL]", text)
        # Remove phone numbers (10+ digits)
        cleaned = re.sub(r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]", cleaned)
        # Remove credit card-like patterns
        cleaned = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[CARD]", cleaned)
        # Remove API keys/passwords/bearer tokens
        cleaned = re.sub(r"\b(ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}|Bearer\s+\S+)\b", "[SECRET]", cleaned)
        # Truncate to safe length
        return cleaned[:140].strip()

    def record_turn(
        self,
        user_id: str,
        role: str,
        text: str,
        category: Optional[EmojiCategory] = None,
        emoji_used: Optional[str] = None,
    ):
        """Records a conversation turn in the bounded sliding window for context awareness."""
        if not user_id:
            return
        user_key = str(user_id)
        if user_key not in self._user_context:
            self._user_context[user_key] = deque(maxlen=self.max_context_turns)
        sanitized = self.sanitize_for_context(text)
        self._user_context[user_key].append(
            ConversationTurn(
                role=role,
                sanitized_text=sanitized,
                category=category,
                emoji_used=emoji_used,
            )
        )

    def get_recent_history(self, user_id: str) -> List[ConversationTurn]:
        """Returns recent conversation history for the user."""
        user_key = str(user_id)
        if user_key in self._user_context:
            return list(self._user_context[user_key])
        return []

    def clear_context(self, user_id: str):
        """Clears memory context for a user."""
        user_key = str(user_id)
        if user_key in self._user_context:
            del self._user_context[user_key]

    def _count_emojis_in_text(self, text: str) -> int:
        """Counts the number of unicode emojis in the text."""
        return len(EMOJI_PATTERN.findall(text))

    def _deterministic_pick(self, text: str, options: List[str]) -> str:
        """
        Deterministically selects an emoji from the allowed category options
        using a stable text hash. The same text always produces the exact same emoji.
        """
        if not options:
            return "🙂"
        if len(options) == 1:
            return options[0]
        # Hash code of text
        h = 0
        for ch in text.strip().lower():
            h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        return options[h % len(options)]

    def analyze_message(
        self,
        text: Optional[str],
        user_id: Optional[str] = None,
        rasa_intent: Optional[str] = None,
    ) -> ReactionAnalysis:
        """
        Analyzes the user's message, intent, emotion, sentiment, and context.
        Returns a structured ReactionAnalysis with category and selected emoji.
        """
        raw_text = (text or "").strip()
        if not raw_text:
            return ReactionAnalysis(
                category=EmojiCategory.NEUTRAL,
                confidence=1.0,
                selected_emoji=None,
                should_react=False,
                reason="Empty message",
            )

        # 0. Check Emoji Spam Density in Input (CRITICAL: Checked FIRST)
        emoji_count = self._count_emojis_in_text(raw_text)
        text_len = len(raw_text)
        emoji_ratio = emoji_count / max(text_len, 1)

        # If user message already contains 3+ emojis or >20% emoji chars, avoid visual spam
        if emoji_count >= 3 or emoji_ratio > 0.20:
            return ReactionAnalysis(
                category=EmojiCategory.NEUTRAL,
                confidence=0.95,
                selected_emoji=None,
                should_react=False,
                reason="Message already contains multiple emojis (spam prevention)",
            )

        # 1. Check Long Technical Content (Avoid reaction spam on long code/logs)
        is_technical = bool(self.re_technical.search(raw_text)) and text_len > 150
        if is_technical or (text_len > 250 and not self.re_happiness.search(raw_text)):
            return ReactionAnalysis(
                category=EmojiCategory.NEUTRAL,
                confidence=0.90,
                selected_emoji=None,
                should_react=False,
                reason="Long technical text / code snippet (avoid reaction spam)",
            )

        # Retrieve Context History
        history = self.get_recent_history(user_id) if user_id else []

        # -------------------------------------------------------------
        # Context-Aware Checks:
        # -------------------------------------------------------------
        # Scenario: User previously celebrated fixing bot, and now shares the ordeal: "It was broken for 3 days 😭"
        if history:
            prev_turns = list(history)
            prev_had_fix = any(
                t.category == EmojiCategory.HAPPINESS_EXCITEMENT
                or bool(self.re_fixed_it.search(t.sanitized_text))
                or t.emoji_used in ["🎉", "🔥", "🤩"]
                for t in prev_turns[-3:]
            )

            re_past_ordeal = re.compile(
                r"\b(broken\s*for|stuck\s*for|took\s*(me\s*)?\d+|tried\s*for|struggled|exhausted|finally|was\s*broken)\b",
                re.IGNORECASE,
            )
            if prev_had_fix and (re_past_ordeal.search(raw_text) or "😭" in raw_text or "😢" in raw_text):
                selected_emoji = "🫂" if "😭" in raw_text else "💙"
                return ReactionAnalysis(
                    category=EmojiCategory.SADNESS,
                    confidence=0.95,
                    selected_emoji=selected_emoji,
                    should_react=True,
                    reason="Contextual empathetic relief following resolved issue",
                    context_adjusted=True,
                )

        # -------------------------------------------------------------
        # Priority Rule Matching:
        # -------------------------------------------------------------

        # A. Laughing / Joke / Humor
        # Example: "😂😂 that's funny", "LOL", "Haha", "that's funny"
        if ("😂" in raw_text or "🤣" in raw_text or "😆" in raw_text) and not self.re_sadness.search(raw_text):
            if "😂" in raw_text and ("funny" in raw_text.lower() or "that's funny" in raw_text.lower()):
                selected_emoji = "🤣"
            else:
                selected_emoji = "🤣" if "🤣" in raw_text else ("😂" if "😂" in raw_text else "😆")
            return ReactionAnalysis(
                category=EmojiCategory.LAUGHING_JOKE,
                confidence=0.98,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Laughter / Joke indicator with emoji or text match",
            )

        if self.re_funny_joke.search(raw_text) and not self.re_sadness.search(raw_text):
            lower = raw_text.lower()
            if "that's funny" in lower or "thats funny" in lower or "hilarious" in lower or "rofl" in lower:
                selected_emoji = "🤣"
            elif "lol" in lower or "lmao" in lower or "haha" in lower:
                selected_emoji = "😂"
            else:
                selected_emoji = self._deterministic_pick(raw_text, ["😂", "🤣", "😆"])
            return ReactionAnalysis(
                category=EmojiCategory.LAUGHING_JOKE,
                confidence=0.95,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Humor / Joke text pattern match",
            )

        # B. Sadness / Grief / Empathy (CRITICAL: Strict safety, supportive emojis only)
        # Examples: "I'm sad", "I'm sad today", "I feel bad", "She left me", "I'm depressed"
        if self.re_sadness_today.search(raw_text) or raw_text.lower().strip() in ["i'm sad today", "i am sad today", "sad today"]:
            return ReactionAnalysis(
                category=EmojiCategory.SADNESS,
                confidence=0.98,
                selected_emoji="😔",
                should_react=True,
                reason="Direct sadness statement (e.g. I'm sad today)",
            )

        if self.re_sadness.search(raw_text) or any(e in raw_text for e in ["😭", "😢", "🥺", "💔", "😔", "😞"]):
            lower = raw_text.lower()
            if "she left me" in lower or "he left me" in lower or "heartbroken" in lower or "broke up" in lower or "💔" in raw_text:
                selected_emoji = "🫂"
            elif "crying" in lower or "😭" in raw_text or "tears" in lower:
                selected_emoji = "😢"
            elif "depressed" in lower or "depression" in lower:
                selected_emoji = "💙"
            elif "i'm sad" in lower or "i am sad" in lower or "i feel bad" in lower:
                selected_emoji = "😔"
            else:
                selected_emoji = self._deterministic_pick(raw_text, ["😔", "😢", "🫂", "💙"])
            return ReactionAnalysis(
                category=EmojiCategory.SADNESS,
                confidence=0.95,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Sadness / Empathy emotion detected",
            )

        # C. Thanks / Gratitude
        # Examples: "Thank you bro", "Thank you", "Thanks", "You're helpful"
        if self.re_thanks_bro.search(raw_text):
            return ReactionAnalysis(
                category=EmojiCategory.THANKS,
                confidence=0.98,
                selected_emoji="🙏",
                reason="Gratitude to brother/friend match",
                should_react=True,
            )

        if self.re_thanks.search(raw_text) or rasa_intent == "thank":
            lower = raw_text.lower()
            if "you're helpful" in lower or "you are helpful" in lower or "helpful" in lower:
                selected_emoji = "😊"
            elif "thank you" in lower or "thanks" in lower or "shukriya" in lower or "dhanyawad" in lower:
                selected_emoji = "🙏"
            else:
                selected_emoji = self._deterministic_pick(raw_text, ["🙏", "😊", "❤️"])
            return ReactionAnalysis(
                category=EmojiCategory.THANKS,
                confidence=0.95,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Gratitude / Thanks expression",
            )

        # D. Love / Affection
        # Examples: "I love you", "You're cute", "Love you"
        if self.re_love.search(raw_text):
            lower = raw_text.lower()
            if "cute" in lower or "adorable" in lower or "sweet" in lower:
                selected_emoji = "🥰"
            elif "kiss" in lower or "muah" in lower:
                selected_emoji = "😘"
            elif "i love you" in lower or "love you" in lower or "love u" in lower or "luv u" in lower:
                selected_emoji = "❤️"
            else:
                selected_emoji = self._deterministic_pick(raw_text, ["❤️", "🥰", "😘", "💕"])
            return ReactionAnalysis(
                category=EmojiCategory.LOVE_AFFECTION,
                confidence=0.96,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Affection / Love expression",
            )

        # E. Happiness / Excitement / Celebration
        # Examples: "That's amazing!", "I got it", "I'm happy", "Wow!"
        if self.re_amazing.search(raw_text):
            return ReactionAnalysis(
                category=EmojiCategory.HAPPINESS_EXCITEMENT,
                confidence=0.98,
                selected_emoji="🤩",
                should_react=True,
                reason="Excitement / Amazing expression match",
            )

        if self.re_fixed_it.search(raw_text):
            return ReactionAnalysis(
                category=EmojiCategory.HAPPINESS_EXCITEMENT,
                confidence=0.98,
                selected_emoji="🎉",
                should_react=True,
                reason="Problem solved / celebration expression",
            )

        if self.re_happiness.search(raw_text) or rasa_intent == "mood_great":
            lower = raw_text.lower()
            if "wow" in lower or "fire" in lower:
                selected_emoji = "🔥"
            elif "i'm happy" in lower or "i am happy" in lower or "happy" in lower:
                selected_emoji = "😊"
            elif "celebrate" in lower or "congrats" in lower or "party" in lower:
                selected_emoji = "🎉"
            elif "excited" in lower or "super stoked" in lower:
                selected_emoji = "😄"
            else:
                selected_emoji = self._deterministic_pick(raw_text, ["😊", "😄", "🤩", "🎉", "🔥"])
            return ReactionAnalysis(
                category=EmojiCategory.HAPPINESS_EXCITEMENT,
                confidence=0.92,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Happiness / Celebration detected",
            )

        # F. Anger / Frustration
        # Examples: "I'm angry", "This is annoying", "WTF", "This isn't working"
        if self.re_anger.search(raw_text):
            lower = raw_text.lower()
            if "wtf" in lower or "what the hell" in lower or "what the fuck" in lower:
                selected_emoji = "🤦"
            elif "this isn't working" in lower or "not working" in lower:
                selected_emoji = "🤦"
            elif "this is annoying" in lower or "annoyed" in lower or "annoying" in lower:
                selected_emoji = "😤"
            elif "i'm angry" in lower or "angry" in lower or "gussa" in lower or "furious" in lower:
                selected_emoji = "😠"
            else:
                selected_emoji = self._deterministic_pick(raw_text, ["😤", "😠", "🤦"])
            return ReactionAnalysis(
                category=EmojiCategory.ANGER_FRUSTRATION,
                confidence=0.95,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Anger / Frustration detected",
            )

        # G. Surprise / Shock
        # Examples: "Really?", "No way!", "What happened?!"
        if self.re_surprise.search(raw_text):
            lower = raw_text.lower()
            if "no way" in lower or "mind blown" in lower or "unbelievable" in lower:
                selected_emoji = "🤯"
            elif "what happened" in lower or "omg" in lower:
                selected_emoji = "😮"
            elif "really" in lower or "for real" in lower:
                selected_emoji = "😳"
            else:
                selected_emoji = self._deterministic_pick(raw_text, ["😳", "😮", "🤯"])
            return ReactionAnalysis(
                category=EmojiCategory.SURPRISE,
                confidence=0.94,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Surprise / Shock detected",
            )

        # H. Confusion / Doubt
        # Examples: "What?", "I don't understand", "How does this work?"
        if self.re_confusion.search(raw_text):
            lower = raw_text.lower()
            if "i don't understand" in lower or "dont understand" in lower or "didn't get it" in lower:
                selected_emoji = "😕"
            elif "what?" in lower or raw_text.strip().lower() in ["what?", "kya?", "huh?"]:
                selected_emoji = "🤔"
            elif "how does this work" in lower:
                selected_emoji = "🤔"
            else:
                selected_emoji = self._deterministic_pick(raw_text, ["🤔", "😕", "❓"])
            return ReactionAnalysis(
                category=EmojiCategory.CONFUSION,
                confidence=0.92,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Confusion / Inquiry detected",
            )

        # I. Greetings
        # Examples: "Hi", "Hello", "Hey", "Namaste", "Good morning", "Hi buddy"
        if self.re_morning.search(raw_text):
            return ReactionAnalysis(
                category=EmojiCategory.GREETINGS,
                confidence=0.98,
                selected_emoji="🌅",
                should_react=True,
                reason="Morning greeting detected",
            )

        if self.re_namaste.search(raw_text):
            return ReactionAnalysis(
                category=EmojiCategory.GREETINGS,
                confidence=0.98,
                selected_emoji="🙏",
                should_react=True,
                reason="Traditional respectful greeting detected",
            )

        if self.re_greeting.search(raw_text) or rasa_intent == "greet":
            lower = raw_text.lower()
            if "hi buddy" in lower or "hey buddy" in lower or "hello" in lower or "hi" in lower or "hey" in lower:
                selected_emoji = "👋"
            else:
                selected_emoji = self._deterministic_pick(raw_text, ["👋", "😊", "🙏"])
            return ReactionAnalysis(
                category=EmojiCategory.GREETINGS,
                confidence=0.95,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Standard greeting detected",
            )

        # J. Agreement / Confirmation
        # Examples: "Okay", "Yes", "Correct", "Got it"
        if self.re_agreement.search(raw_text) or (rasa_intent == "affirm" and text_len < 30):
            lower = raw_text.lower().strip()
            if "correct" in lower:
                selected_emoji = "✅"
            elif "got it" in lower or "perfect" in lower:
                selected_emoji = "👌"
            elif "yes" in lower or "okay" in lower or "ok" in lower:
                selected_emoji = "👍"
            else:
                selected_emoji = self._deterministic_pick(raw_text, ["👍", "✅", "👌"])
            return ReactionAnalysis(
                category=EmojiCategory.AGREEMENT_CONFIRMATION,
                confidence=0.95,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Agreement / Confirmation detected",
            )

        # K. Disagreement / Rejection
        # Examples: "No", "Wrong", "I don't want this"
        if self.re_disagreement.search(raw_text) or (rasa_intent == "deny" and text_len < 30):
            lower = raw_text.lower().strip()
            if "wrong" in lower or "incorrect" in lower or "no" in lower:
                selected_emoji = "❌"
            elif "i don't want this" in lower or "dont want this" in lower:
                selected_emoji = "👎"
            else:
                selected_emoji = self._deterministic_pick(raw_text, ["❌", "👎", "😐"])
            return ReactionAnalysis(
                category=EmojiCategory.DISAGREEMENT_REJECTION,
                confidence=0.95,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Disagreement / Rejection detected",
            )

        # L. Questions (Informational)
        # Examples: "What is Python?", "How does an engine work?"
        # Prefer: "🤔 💡" (Do NOT automatically use a question-mark emoji for every question)
        if self.re_question_start.search(raw_text) or (raw_text.endswith("?") and not self.re_confusion.search(raw_text)):
            lower = raw_text.lower()
            if "what is python" in lower or "what is" in lower:
                selected_emoji = "🤔"
            elif "how to" in lower or "explain" in lower:
                selected_emoji = "💡"
            else:
                selected_emoji = self._deterministic_pick(raw_text, ["🤔", "💡"])
            
            return ReactionAnalysis(
                category=EmojiCategory.QUESTION,
                confidence=0.90,
                selected_emoji=selected_emoji,
                should_react=True,
                reason="Informational question pattern match",
            )

        # M. Neutral Fallback
        # If emotion is unclear, use subtle emoji or no emoji
        return ReactionAnalysis(
            category=EmojiCategory.NEUTRAL,
            confidence=0.50,
            selected_emoji="🙂" if text_len < 40 else None,
            should_react=bool(text_len < 40),
            reason="Neutral statement",
        )

    def get_reaction(
        self,
        text: Optional[str],
        user_id: Optional[str] = None,
        rasa_intent: Optional[str] = None,
        force: bool = False,
    ) -> Optional[str]:
        """
        Main public interface: analyzes message and returns the chosen emoji reaction
        or None if no reaction should be posted.
        Guarantees deterministic, context-aware emoji selection without random global fallback.
        """
        analysis = self.analyze_message(text, user_id=user_id, rasa_intent=rasa_intent)
        
        # Record turn for context tracking
        if user_id and text:
            self.record_turn(
                user_id=user_id,
                role="user",
                text=text,
                category=analysis.category,
                emoji_used=analysis.selected_emoji if (analysis.should_react or force) else None,
            )

        if force:
            return analysis.selected_emoji or "👍"

        if analysis.should_react and analysis.selected_emoji:
            return analysis.selected_emoji

        return None

    def get_fallback_emoji(self, category_or_emoji: Optional[str]) -> str:
        """
        Returns a Telegram-supported fallback reaction emoji guaranteed to be logically
        aligned with the detected category, avoiding any random global selection.
        """
        # If passed an EmojiCategory
        if isinstance(category_or_emoji, EmojiCategory):
            fallbacks = CATEGORY_TELEGRAM_FALLBACKS.get(category_or_emoji, ["👍"])
            return fallbacks[0]

        # If passed an emoji that is already in standard fallback or telegram reactions:
        if category_or_emoji in ["👍", "🙏", "❤️", "🔥", "🎉", "👏", "💯", "😎", "😁", "😢", "😡", "🤔"]:
            return category_or_emoji

        # If passed an emoji string, find its category
        for cat, emojis in CATEGORY_EMOJIS.items():
            if category_or_emoji in emojis:
                fallbacks = CATEGORY_TELEGRAM_FALLBACKS.get(cat, ["👍"])
                return fallbacks[0]

        return "👍"


# Singleton instance
_GLOBAL_EMOJI_MANAGER: Optional[EmojiReactionManager] = None


def get_emoji_reaction_manager() -> EmojiReactionManager:
    """Returns singleton instance of EmojiReactionManager."""
    global _GLOBAL_EMOJI_MANAGER
    if _GLOBAL_EMOJI_MANAGER is None:
        _GLOBAL_EMOJI_MANAGER = EmojiReactionManager()
    return _GLOBAL_EMOJI_MANAGER
