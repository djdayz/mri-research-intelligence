from mrinsight.relevance.tfidf import (
    TFIDF_TOPIC_MODEL_VERSION,
    TfidfTopicBaseline,
)


def test_tfidf_baseline_trains_predicts_and_reports_metadata() -> None:
    model = TfidfTopicBaseline()
    model.fit(
        texts=[
            "BOLD CVR mapping with breath hold MRI",
            "Compressed sensing MRI reconstruction with k-space data",
            "Deep learning segmentation for brain MRI",
            "Transformer model for retail demand forecasting",
        ],
        labels=[
            "cvr",
            "mri_reconstruction",
            "general_mri_ml",
            "unrelated",
        ],
    )

    prediction = model.predict("k-space compressed sensing reconstruction")
    metadata = model.metadata()

    assert prediction.label == "mri_reconstruction"
    assert 0 <= prediction.confidence <= 1
    assert prediction.model_version == TFIDF_TOPIC_MODEL_VERSION
    assert metadata["model_version"] == TFIDF_TOPIC_MODEL_VERSION
    assert metadata["vectorizer"]["ngram_range"] == (1, 2)
