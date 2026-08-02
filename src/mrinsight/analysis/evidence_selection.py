from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from mrinsight.papers import SectionType, StoredPaperChunk
from mrinsight.relevance import TerminologyMatcher, load_default_ontology

EVIDENCE_SELECTOR_VERSION = "analysis-evidence-selector-v1"


class AnalysisFocus(StrEnum):
    """Analysis subtask focus used for deterministic evidence ranking."""

    GENERAL = "general"
    METHODS = "methods"
    RESULTS = "results"
    LIMITATIONS = "limitations"
    ACQUISITION = "acquisition"
    BACKGROUND = "background"


@dataclass(frozen=True, slots=True)
class SelectedEvidence:
    """Deterministic selected evidence set and reproducibility metadata."""

    chunks: tuple[StoredPaperChunk, ...]
    selector_version: str
    prompt_budget: int
    estimated_tokens: int
    selection_checksum: str


class EvidenceSelectionService:
    """Select a bounded, deterministic set of evidence chunks for LLM analysis."""

    def __init__(
        self,
        *,
        max_prompt_tokens: int = 1600,
        focus: AnalysisFocus = AnalysisFocus.GENERAL,
    ) -> None:
        if max_prompt_tokens < 1:
            raise ValueError("max_prompt_tokens must be at least 1.")

        _ontology_version, terms = load_default_ontology()
        self._matcher = TerminologyMatcher(terms)
        self._max_prompt_tokens = max_prompt_tokens
        self._focus = focus

    def select(
        self,
        chunks: tuple[StoredPaperChunk, ...],
    ) -> SelectedEvidence:
        """Return selected chunks within the configured prompt budget."""

        candidates = [
            chunk
            for chunk in chunks
            if chunk.section_type is not SectionType.REFERENCES
        ]
        ordered = sorted(
            candidates,
            key=lambda chunk: (
                -self._score_chunk(chunk),
                chunk.section_type.value,
                chunk.sequence_number,
                chunk.id,
            ),
        )

        selected: list[StoredPaperChunk] = []
        seen_chunk_ids: set[int] = set()
        estimated_tokens = 0

        for chunk in ordered:
            if chunk.id in seen_chunk_ids:
                continue

            chunk_tokens = estimate_prompt_tokens(chunk.text)
            if selected and estimated_tokens + chunk_tokens > self._max_prompt_tokens:
                continue

            selected.append(chunk)
            seen_chunk_ids.add(chunk.id)
            estimated_tokens += chunk_tokens

            if estimated_tokens >= self._max_prompt_tokens:
                break

        stable = tuple(sorted(selected, key=lambda chunk: chunk.sequence_number))

        return SelectedEvidence(
            chunks=stable,
            selector_version=EVIDENCE_SELECTOR_VERSION,
            prompt_budget=self._max_prompt_tokens,
            estimated_tokens=estimated_tokens,
            selection_checksum=build_selection_checksum(stable),
        )

    def _score_chunk(
        self,
        chunk: StoredPaperChunk,
    ) -> float:
        """Score one chunk for analysis evidence selection."""

        matches = self._matcher.find_matches(chunk.text)
        relevance_score = sum(match.weight for match in matches)
        section_score = _section_priority(self._focus, chunk.section_type)
        length_score = min(chunk.token_count / 120.0, 1.0)

        return section_score + relevance_score + length_score


def estimate_prompt_tokens(
    text: str,
) -> int:
    """Return a deterministic approximate prompt-token count."""

    return max(1, round(len(text.split()) * 1.35))


def build_selection_checksum(
    chunks: tuple[StoredPaperChunk, ...],
) -> str:
    """Return checksum for selected chunk identity and ordering."""

    payload = [
        {
            "id": chunk.id,
            "paper_content_id": chunk.paper_content_id,
            "section": chunk.section_type.value,
            "sequence_number": chunk.sequence_number,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
            "chunker_version": chunk.chunker_version,
        }
        for chunk in chunks
    ]
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _section_priority(
    focus: AnalysisFocus,
    section: SectionType,
) -> float:
    """Return focus-specific section priority."""

    focus_priorities: dict[AnalysisFocus, dict[SectionType, float]] = {
        AnalysisFocus.GENERAL: {
            SectionType.ABSTRACT: 5.0,
            SectionType.METHODS: 4.5,
            SectionType.RESULTS: 4.5,
            SectionType.DISCUSSION: 3.5,
            SectionType.INTRODUCTION: 3.0,
        },
        AnalysisFocus.METHODS: {
            SectionType.METHODS: 6.0,
            SectionType.RESULTS: 3.5,
            SectionType.ABSTRACT: 3.0,
        },
        AnalysisFocus.RESULTS: {
            SectionType.RESULTS: 6.0,
            SectionType.DISCUSSION: 4.0,
            SectionType.METHODS: 3.0,
        },
        AnalysisFocus.LIMITATIONS: {
            SectionType.LIMITATIONS: 6.0,
            SectionType.DISCUSSION: 4.5,
            SectionType.CONCLUSION: 3.0,
        },
        AnalysisFocus.ACQUISITION: {
            SectionType.METHODS: 6.0,
            SectionType.ABSTRACT: 3.0,
        },
        AnalysisFocus.BACKGROUND: {
            SectionType.BACKGROUND: 6.0,
            SectionType.INTRODUCTION: 5.0,
            SectionType.ABSTRACT: 3.0,
        },
    }

    return focus_priorities[focus].get(section, 1.0)
