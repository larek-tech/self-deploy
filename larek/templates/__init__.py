"""Шаблоны для генерации проектов."""

from larek.templates.base import LanguageTemplate
from larek.templates.go import GoTemplate
from larek.templates.java import JavaTemplate
from larek.templates.javascript import JavaScriptTemplate
from larek.templates.python import PythonTemplate

__all__ = [
    "LanguageTemplate",
    "GoTemplate",
    "JavaTemplate",
    "JavaScriptTemplate",
    "PythonTemplate",
]
