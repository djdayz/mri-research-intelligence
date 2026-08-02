from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

TFIDF_TOPIC_MODEL_VERSION = "tfidf-topic-baseline-v1"


@dataclass(frozen=True, slots=True)
class TfidfPrediction:
    """One deterministic TF-IDF topic prediction."""

    label: str
    confidence: float
    model_version: str


class TfidfTopicBaseline:
    """Small interpretable TF-IDF baseline for topic triage."""

    def __init__(
        self,
        *,
        model_version: str = TFIDF_TOPIC_MODEL_VERSION,
    ) -> None:
        self._model_version = model_version
        pipeline_class = import_module("sklearn.pipeline").Pipeline
        vectorizer_class = import_module(
            "sklearn.feature_extraction.text"
        ).TfidfVectorizer
        classifier_class = import_module("sklearn.linear_model").LogisticRegression

        self._pipeline = pipeline_class(
            steps=[
                (
                    "tfidf",
                    vectorizer_class(
                        analyzer="word",
                        ngram_range=(1, 2),
                        lowercase=True,
                        strip_accents="unicode",
                        min_df=1,
                    ),
                ),
                (
                    "classifier",
                    classifier_class(
                        random_state=17,
                        max_iter=500,
                        solver="lbfgs",
                    ),
                ),
            ]
        )

    @property
    def model_version(self) -> str:
        """Return the model version."""

        return self._model_version

    def fit(
        self,
        texts: list[str],
        labels: list[str],
    ) -> TfidfTopicBaseline:
        """Train the deterministic baseline on caller-provided fixture data."""

        self._pipeline.fit(texts, labels)
        return self

    def predict(
        self,
        text: str,
    ) -> TfidfPrediction:
        """Predict one topic label and confidence."""

        classifier = self._pipeline.named_steps["classifier"]

        prediction = str(self._pipeline.predict([text])[0])
        probabilities = self._pipeline.predict_proba([text])[0]
        class_index = list(classifier.classes_).index(prediction)

        return TfidfPrediction(
            label=prediction,
            confidence=round(float(probabilities[class_index]), 3),
            model_version=self._model_version,
        )

    def metadata(self) -> dict[str, Any]:
        """Return serialisable model metadata."""

        vectorizer = self._pipeline.named_steps["tfidf"]
        classifier = self._pipeline.named_steps["classifier"]

        return {
            "model_version": self._model_version,
            "vectorizer": {
                "analyzer": vectorizer.analyzer,
                "ngram_range": vectorizer.ngram_range,
                "strip_accents": vectorizer.strip_accents,
            },
            "classifier": {
                "type": classifier.__class__.__name__,
                "random_state": classifier.random_state,
                "solver": classifier.solver,
            },
        }
