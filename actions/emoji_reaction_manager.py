"""
Emoji Reaction Manager proxy export for actions package.
"""
from addons.emoji_reaction_manager import (
    EmojiReactionManager,
    EmojiCategory,
    ReactionAnalysis,
    CATEGORY_EMOJIS,
    CATEGORY_TELEGRAM_FALLBACKS,
    get_emoji_reaction_manager,
)

__all__ = [
    "EmojiReactionManager",
    "EmojiCategory",
    "ReactionAnalysis",
    "CATEGORY_EMOJIS",
    "CATEGORY_TELEGRAM_FALLBACKS",
    "get_emoji_reaction_manager",
]
