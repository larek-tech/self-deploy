"""Анализаторы проектов в зависимости от языка программирования"""

from .base import BaseAnalyzer
from .go import GoAnalyzer
from .java import JavaAnalyzer
from .kotlin import KotlinAnalyzer
from .javascript import JavaScriptAnalyzer

__all__ = [
    "BaseAnalyzer",
    "GoAnalyzer",
    "JavaAnalyzer",
    "KotlinAnalyzer",
    "JavaScriptAnalyzer",
]
