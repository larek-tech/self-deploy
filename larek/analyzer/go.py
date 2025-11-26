import typing as tp
from pathlib import Path
from larek.analyzer import BaseAnalyzer
from larek.models import Service


class GoAnalyzer(BaseAnalyzer):
    def analyze(self, root: Path) -> tp.Optional[Service]:
        return None
