from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib.resources import files

from mrinsight.analysis.llm import LLMEvidenceChunk
from mrinsight.analysis.schema import ANALYSIS_SCHEMA_VERSION
from mrinsight.papers import AnalysisScope

ANALYSIS_PROMPT_VERSION = "analysis-prompt-v1"
REPAIR_PROMPT_VERSION = "analysis-repair-prompt-v1"


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """Loaded prompt file and reproducibility metadata."""

    version: str
    text: str
    checksum: str


def load_analysis_prompt() -> PromptTemplate:
    """Load the analysis prompt template."""

    return _load_prompt(
        filename="analysis_v1.md",
        version=ANALYSIS_PROMPT_VERSION,
    )


def load_repair_prompt() -> PromptTemplate:
    """Load the repair prompt template."""

    return _load_prompt(
        filename="repair_v1.md",
        version=REPAIR_PROMPT_VERSION,
    )


def build_analysis_user_prompt(
    *,
    paper_id: int,
    content_id: int,
    analysis_scope: AnalysisScope,
    source_checksum: str,
    chunks: tuple[LLMEvidenceChunk, ...],
) -> tuple[str, str]:
    """Build deterministic user prompt text and input checksum."""

    payload = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "paper_id": paper_id,
        "content_id": content_id,
        "analysis_scope": analysis_scope.value,
        "source_checksum": source_checksum,
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "section": chunk.section.value,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "start_page": chunk.start_page,
                "end_page": chunk.end_page,
                "text": chunk.text,
            }
            for chunk in chunks
        ],
    }
    prompt = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return prompt, _sha256_text(prompt)


def build_repair_user_prompt(
    *,
    original_user_prompt: str,
    previous_response: str,
    validation_errors: tuple[str, ...],
) -> tuple[str, str]:
    """Build deterministic repair prompt text and input checksum."""

    payload = {
        "original_request": json.loads(original_user_prompt),
        "previous_response": previous_response,
        "validation_errors": validation_errors,
    }
    prompt = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return prompt, _sha256_text(prompt)


def _load_prompt(
    *,
    filename: str,
    version: str,
) -> PromptTemplate:
    """Load a bundled prompt file."""

    text = (
        files("mrinsight.analysis.prompts")
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )

    return PromptTemplate(
        version=version,
        text=text,
        checksum=_sha256_text(text),
    )


def _sha256_text(
    text: str,
) -> str:
    """Return a SHA-256 checksum for prompt reproducibility."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()
