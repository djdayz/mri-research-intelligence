from mrinsight.relevance.terminology import (
    TerminologyMatcher,
    load_default_ontology,
)


def make_matcher() -> TerminologyMatcher:
    """Create the default ontology matcher."""

    _version, terms = load_default_ontology()
    return TerminologyMatcher(terms)


def test_matcher_handles_case_punctuation_and_hyphen_variation() -> None:
    matcher = make_matcher()

    matches = matcher.find_matches(
        "A cvr study used breath hold and end-tidal CO₂ during 3T MRI."
    )

    assert [match.concept_id for match in matches] == [
        "cvr",
        "cvr",
        "cvr",
        "mri_general",
        "mri_general",
    ]


def test_matcher_avoids_substring_false_positives() -> None:
    matcher = make_matcher()

    assert matcher.find_matches("premriword and cvresponse are unrelated tokens") == ()


def test_matcher_prefers_longer_overlapping_terms() -> None:
    matcher = make_matcher()

    matches = matcher.find_matches("BOLD CVR mapping was estimated.")

    assert [(match.alias, match.concept_id) for match in matches] == [
        ("BOLD CVR", "cvr")
    ]


def test_matcher_is_deterministic() -> None:
    matcher = make_matcher()
    text = "Compressed sensing MRI reconstruction with SENSE at 7 T."

    first = matcher.find_matches(text)
    second = matcher.find_matches(text)

    assert first == second
