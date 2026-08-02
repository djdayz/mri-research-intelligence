from typing import Protocol

from mrinsight.analysis.records import (
    NewLLMRun,
    NewPaperAnalysis,
    StoredLLMRun,
    StoredPaperAnalysis,
)
from mrinsight.papers import AnalysisScope


class LLMRunRepository(Protocol):
    """Persistence contract for LLM runs."""

    def add(
        self,
        run: NewLLMRun,
    ) -> StoredLLMRun:
        """Persist one LLM run without committing."""


class PaperAnalysisRepository(Protocol):
    """Persistence contract for paper analyses."""

    def get_current(
        self,
        *,
        paper_id: int,
        paper_content_id: int,
        analysis_scope: AnalysisScope,
        content_checksum: str,
        selected_evidence_checksum: str,
        schema_version: str,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> StoredPaperAnalysis | None:
        """Return a cached analysis for the exact reproducibility identity."""

    def list_by_paper(
        self,
        paper_id: int,
    ) -> tuple[StoredPaperAnalysis, ...]:
        """Return analyses for one paper ordered newest first."""

    def get_by_id(
        self,
        analysis_id: int,
    ) -> StoredPaperAnalysis | None:
        """Return one analysis by database identity."""

    def add(
        self,
        analysis: NewPaperAnalysis,
    ) -> StoredPaperAnalysis:
        """Persist one paper analysis without committing."""
