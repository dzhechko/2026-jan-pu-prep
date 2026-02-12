"""Import all models so Alembic can discover them via Base.metadata."""

from app.models.base import Base
from app.models.user import User
from app.models.ai_profile import AIProfile
from app.models.food_entry import FoodEntry
from app.models.pattern import Pattern
from app.models.insight import Insight
from app.models.lesson import CBTLesson, UserLessonProgress
from app.models.subscription import Subscription
from app.models.invite import Invite
from app.models.chat_message import ChatMessage

__all__ = [
    "Base",
    "User",
    "AIProfile",
    "FoodEntry",
    "Pattern",
    "Insight",
    "CBTLesson",
    "UserLessonProgress",
    "Subscription",
    "Invite",
    "ChatMessage",
]
