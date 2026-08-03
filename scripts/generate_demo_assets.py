from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from io import BytesIO
from pathlib import Path

from mrinsight.analysis import (
    AnalysisEvidenceValidator,
    FakeLLMProvider,
    GeneratePaperAnalysisService,
    LLMEvidenceChunk,
    LLMRequest,
)
from mrinsight.discovery import (
    DigestPaper,
    render_digest_html,
    render_digest_plain_text,
)
from mrinsight.evaluation import run_evaluation
from mrinsight.evaluation.fixtures import load_golden_evaluation_cases

ASSET_DIR = Path("docs/demo-assets")
FIXED_GENERATED_AT = "2026-08-03T00:00:00+00:00"


def main() -> None:
    """Generate synthetic, credentials-free portfolio demo assets."""

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    _write_synthetic_pdf()
    _write_api_requests()
    _write_fake_provider_response()
    _write_analysis_output()
    _write_digest_outputs()
    _write_cli_transcript()


def _write_synthetic_pdf() -> None:
    pdf = _build_text_pdf(
        (
            (
                "Synthetic MRI CVR Demonstration Paper",
                "Abstract",
                "This generated PDF describes a permitted synthetic BOLD MRI study.",
                "Methods used a carbon dioxide challenge and CVR mapping.",
                "Results reported 2.5 units of signal change in the supplied text.",
            ),
            (
                "Limitations",
                "This is not a real paper and contains no private source material.",
                "It exists only to demonstrate upload, extraction, and chunking.",
            ),
        )
    )
    (ASSET_DIR / "synthetic-mri-cvr-paper.pdf").write_bytes(pdf)


def _write_api_requests() -> None:
    (ASSET_DIR / "sample-api-requests.http").write_text(
        """# MRInsight local demo requests.

### Health
GET http://localhost:8000/health

### Readiness
GET http://localhost:8000/ready

### Ingest DOI metadata
POST http://localhost:8000/papers
content-type: application/json

{"doi":"10.1234/synthetic-demo"}

### Upload permitted synthetic PDF
POST http://localhost:8000/papers/1/full-text
content-type: multipart/form-data

file=@docs/demo-assets/synthetic-mri-cvr-paper.pdf;type=application/pdf

### Compute deterministic relevance
POST http://localhost:8000/papers/1/relevance

### Generate fake-provider analysis
POST http://localhost:8000/papers/1/analysis

### Manual digest preview
POST http://localhost:8000/subscriptions/1/digest-preview
content-type: application/json

{"period_start":"2026-01-01","period_end":"2026-01-31","rows":10}
""",
        encoding="utf-8",
    )


def _write_fake_provider_response() -> None:
    case = load_golden_evaluation_cases()[0]
    chunk = case.chunks[0]
    request = LLMRequest(
        paper_id=case.paper.id,
        content_id=case.content.id,
        analysis_scope=case.analysis_scope,
        source_checksum=case.content.checksum,
        schema_version="paper-analysis-schema-v1",
        prompt_version="portfolio-demo-v1",
        prompt_checksum="0" * 64,
        model_identifier="fake-analysis-model-v1",
        system_prompt="Return evidence-linked scientific analysis JSON.",
        user_prompt=chunk.text,
        input_checksum=case.content.checksum,
        chunks=(
            LLMEvidenceChunk(
                chunk_id=chunk.id,
                paper_id=chunk.paper_id,
                content_id=chunk.paper_content_id,
                section=chunk.section_type,
                text=chunk.text,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                start_page=chunk.page_number,
                end_page=chunk.end_page_number,
            ),
        ),
    )
    response = FakeLLMProvider().complete(request)
    payload = {
        "provider": response.provider_name,
        "model": response.model_identifier,
        "provider_request_id": "redacted-demo-id",
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "latency_ms": response.latency_ms,
        "raw_json": json.loads(response.raw_text),
    }
    _write_json("sample-fake-provider-response.json", payload)


def _write_analysis_output() -> None:
    case = load_golden_evaluation_cases()[0]
    service = GeneratePaperAnalysisService(
        provider=FakeLLMProvider(),
        validator=AnalysisEvidenceValidator(),
        model_identifier="fake-analysis-model-v1",
    )
    result = service.execute(
        paper=case.paper,
        content=case.content,
        analysis_scope=case.analysis_scope,
        chunks=case.chunks,
    )
    if result.analysis is None:
        raise RuntimeError("Fake provider did not produce a valid analysis.")

    _write_json(
        "sample-analysis-output.json",
        {
            "status": result.status.value,
            "repair_attempt_count": result.repair_attempt_count,
            "analysis": result.analysis.model_dump(mode="json"),
        },
    )

    report = run_evaluation(
        provider_mode="fake",
        model_identifier="fake-analysis-model-v1",
    )
    report_payload = asdict(report)
    report_payload["generated_at"] = FIXED_GENERATED_AT
    _write_json("sample-fake-evaluation-report.json", report_payload)


def _write_digest_outputs() -> None:
    paper = DigestPaper(
        paper_id=101,
        doi="10.1234/synthetic-eval",
        title="Synthetic BOLD MRI cerebrovascular reactivity study",
        journal="Synthetic Evaluation Journal",
        publication_date=date(2026, 5, 1),
        relevance_score=0.91,
        analysis_scope="abstract_only",
        concise_summary=(
            "Synthetic evidence describes a BOLD MRI CVR mapping workflow with "
            "explicit abstract-only provenance."
        ),
        methodology_highlights=(
            "Carbon dioxide challenge MRI",
            "Section-aware evidence chunking",
        ),
        main_results=("Reported 2.5 units of signal change in supplied evidence.",),
        limitations=("Generated demonstration record, not a real paper.",),
        link="https://doi.org/10.1234/synthetic-eval",
        provenance="Synthetic fixture generated by MRInsight.",
        ranking_explanation="High MRI and CVR terminology overlap with topic rules.",
    )
    title = "Demo MRI CVR weekly digest"
    (ASSET_DIR / "sample-digest.txt").write_text(
        render_digest_plain_text(title=title, papers=(paper,)),
        encoding="utf-8",
    )
    (ASSET_DIR / "sample-digest.html").write_text(
        render_digest_html(title=title, papers=(paper,)),
        encoding="utf-8",
    )


def _write_cli_transcript() -> None:
    (ASSET_DIR / "sample-cli-transcript.txt").write_text(
        """$ .venv/bin/python -m alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.

$ .venv/bin/python -m mrinsight.cli seed demo
Created demo subscription 1.

$ MRINSIGHT_LLM_PROVIDER=fake .venv/bin/python -m mrinsight.cli eval run \\
  --output var/evaluation/golden-report.json
{
  "provider_mode": "fake",
  "summary": {
    "total_cases": 5,
    "failed_cases": 0,
    "pass_rate": 1.0
  }
}

$ .venv/bin/python -m mrinsight.cli digest run --subscription-id 1 --rows 10
Created digest 1 with 1 papers.
""",
        encoding="utf-8",
    )


def _write_json(
    filename: str,
    payload: object,
) -> None:
    (ASSET_DIR / filename).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _build_text_pdf(
    pages: tuple[tuple[str, ...], ...],
) -> bytes:
    objects: dict[int, bytes] = {}
    page_ids: list[int] = []
    content_ids: list[int] = []
    next_object_id = 3

    for _ in pages:
        page_ids.append(next_object_id)
        content_ids.append(next_object_id + 1)
        next_object_id += 2

    font_id = next_object_id
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode()

    for page_id, content_id, lines in zip(page_ids, content_ids, pages, strict=True):
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode()
        stream = _build_text_stream(lines)
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )

    objects[font_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    return _serialize_pdf(objects)


def _build_text_stream(
    lines: tuple[str, ...],
) -> bytes:
    commands = ["BT", "/F1 12 Tf", "72 720 Td"]
    for index, line in enumerate(lines):
        if index:
            commands.append("0 -18 Td")
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({escaped}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1")


def _serialize_pdf(
    objects: dict[int, bytes],
) -> bytes:
    pdf = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}

    for object_id in sorted(objects):
        offsets[object_id] = len(pdf)
        pdf.extend(f"{object_id} 0 obj\n".encode())
        pdf.extend(objects[object_id])
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    object_count = max(objects) + 1
    xref = BytesIO()
    xref.write(f"xref\n0 {object_count}\n".encode())
    xref.write(b"0000000000 65535 f \n")
    for object_id in range(1, object_count):
        xref.write(f"{offsets[object_id]:010d} 00000 n \n".encode())
    xref.write(
        (
            f"trailer\n<< /Size {object_count} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    pdf.extend(xref.getvalue())
    return bytes(pdf)


if __name__ == "__main__":
    main()
