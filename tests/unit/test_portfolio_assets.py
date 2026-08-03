import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
ASSETS = DOCS / "demo-assets"


def test_portfolio_case_study_covers_employer_review_topics() -> None:
    case_study = (DOCS / "portfolio-case-study.md").read_text(encoding="utf-8")

    required_sections = (
        "## Problem",
        "## Users",
        "## Architecture",
        "## Engineering Challenges",
        "## Scientific-Safety Choices",
        "## Deterministic Versus LLM Responsibilities",
        "## Testing Strategy",
        "## Deployment",
        "## Demonstration Assets",
        "## Trade-Offs",
        "## Future Improvements",
        "## Employer-Facing Review",
    )

    for section in required_sections:
        assert section in case_study

    assert "ML engineer" in case_study
    assert "research software engineer" in case_study
    assert "medical-imaging R&D engineer" in case_study
    assert "applied AI engineer" in case_study


def test_architecture_doc_contains_required_mermaid_diagrams() -> None:
    architecture = (DOCS / "architecture.md").read_text(encoding="utf-8")

    assert architecture.count("```mermaid") >= 7
    for label in (
        "## Component Architecture",
        "## DOI Ingestion",
        "## PDF Extraction",
        "## Analysis",
        "## Discovery And Digest",
        "## Data Model",
        "## Deployment",
    ):
        assert label in architecture


def test_demo_assets_are_present_and_synthetic() -> None:
    expected_assets = (
        "synthetic-mri-cvr-paper.pdf",
        "sample-api-requests.http",
        "sample-fake-provider-response.json",
        "sample-analysis-output.json",
        "sample-fake-evaluation-report.json",
        "sample-digest.txt",
        "sample-digest.html",
        "sample-cli-transcript.txt",
    )

    for filename in expected_assets:
        assert (ASSETS / filename).is_file()

    pdf = (ASSETS / "synthetic-mri-cvr-paper.pdf").read_bytes()
    assert pdf.startswith(b"%PDF-1.7")
    assert b"Synthetic MRI CVR Demonstration Paper" in pdf


def test_sample_json_assets_match_fake_provider_contracts() -> None:
    fake_response = json.loads(
        (ASSETS / "sample-fake-provider-response.json").read_text(encoding="utf-8")
    )
    analysis_output = json.loads(
        (ASSETS / "sample-analysis-output.json").read_text(encoding="utf-8")
    )
    evaluation = json.loads(
        (ASSETS / "sample-fake-evaluation-report.json").read_text(encoding="utf-8")
    )

    assert fake_response["provider"] == "fake"
    assert fake_response["raw_json"]["analysis_scope"] == "abstract_only"
    assert analysis_output["status"] == "valid"
    assert analysis_output["analysis"]["objective"]["evidence_references"]
    assert evaluation["provider_mode"] == "fake"
    assert evaluation["summary"]["failed_cases"] == 0


def test_portfolio_docs_do_not_contain_stale_gap_language() -> None:
    stale_phrases = (
        "remain future work",
        "not yet implemented",
        "Implement Milestone 12",
        "Docker support is added",
    )
    checked_files = (
        DOCS / "portfolio-case-study.md",
        DOCS / "implementation-audit.md",
        DOCS / "implementation-progress.md",
        DOCS / "deployment.md",
        ROOT / "README.md",
    )

    for path in checked_files:
        text = path.read_text(encoding="utf-8")
        for phrase in stale_phrases:
            assert phrase not in text


def test_implementation_progress_lists_every_late_substep() -> None:
    progress = (DOCS / "implementation-progress.md").read_text(encoding="utf-8")

    for label in (
        "12A: Concurrent duplicate recovery",
        "12B: Complete end-to-end test",
        "12C: Migration and CI hardening",
        "12D: Structured logging and baseline observability",
        "12E: README, architecture, and API documentation",
        "12F: Release candidate and demo workflow",
        "13A: Real delivery adapter",
        "13B: Scheduled execution",
        "13C: Delivery idempotency and retry",
        "14A: Golden evaluation set",
        "14B: Automated regression evaluation",
        "14C: Cost, latency, and quality metrics",
        "15A: Docker",
        "15B: Cloud deployment configuration",
        "15C: Production database and secrets",
        "15D: CI/CD",
        "16A: Portfolio case study",
        "16B: Architecture visuals",
        "16C: Demonstration assets",
        "16D: Employer-facing quality review",
    ):
        assert label in progress
