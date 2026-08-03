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
