from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from time import perf_counter
from typing import Any

from mrinsight.application.services.analyze_paper import (
    AnalyzePaperService,
    PaperAnalysisOutcome,
)
from mrinsight.application.services.assess_relevance import AssessPaperRelevanceService
from mrinsight.application.services.build_paper_chunks import BuildPaperChunksService
from mrinsight.application.services.ingest_full_text import PaperNotFoundError
from mrinsight.application.services.select_analysis_content import (
    NoAnalyzableContentError,
)
from mrinsight.application.services.store_abstract_content import (
    StoreAbstractContentService,
)
from mrinsight.core.logging import log_event
from mrinsight.discovery import (
    DeliveryStatus,
    DigestPaper,
    DigestRunResult,
    DigestStatus,
    DiscoveryCandidate,
    DiscoveryCandidateStatus,
    DiscoveryProvider,
    DiscoveryProviderError,
    DiscoveryRepository,
    DiscoveryRunStatus,
    DiscoverySearchRequest,
    NewSubscription,
    StoredDigest,
    StoredDigestDelivery,
    StoredDiscoveryCandidate,
    StoredSubscription,
)
from mrinsight.discovery.delivery import (
    DigestDeliveryProvider,
    render_digest_html,
    render_digest_plain_text,
)
from mrinsight.papers import NewPaper, normalize_doi, normalize_title


class SubscriptionNotFoundError(RuntimeError):
    """Raised when a subscription does not exist."""


@dataclass(frozen=True, slots=True)
class CreateSubscriptionService:
    """Create a discovery subscription."""

    repository: DiscoveryRepository

    def execute(
        self,
        subscription: NewSubscription,
    ) -> StoredSubscription:
        """Persist one subscription."""

        return self.repository.add_subscription(subscription)


@dataclass(frozen=True, slots=True)
class RunDigestPreviewService:
    """Run discovery and create a digest preview for one subscription."""

    discovery_repository: DiscoveryRepository
    abstract_content_service: StoreAbstractContentService
    chunk_service: BuildPaperChunksService
    relevance_service: AssessPaperRelevanceService
    discovery_provider: DiscoveryProvider
    delivery_provider: DigestDeliveryProvider
    analysis_service: AnalyzePaperService | None = None
    delivery_retry_delay_seconds: int = 900

    def execute(
        self,
        *,
        subscription_id: int,
        period_start: date | None = None,
        period_end: date | None = None,
        rows: int = 20,
    ) -> DigestRunResult:
        """Run discovery, ranking, digest rendering, and preview delivery."""

        subscription = self.discovery_repository.get_subscription(subscription_id)
        if subscription is None:
            raise SubscriptionNotFoundError(
                f"Subscription {subscription_id} does not exist."
            )

        today = datetime.now(UTC).date()
        end_date = period_end or today
        start_date = period_start or end_date - timedelta(days=7)
        topics = subscription.topics or ()
        run_targets = topics or (None,)
        runs = []
        persisted_candidates = []

        for topic in run_targets:
            query = _combined_query(
                subscription.discovery_query, topic.query if topic else ""
            )
            run = self.discovery_repository.add_discovery_run(
                subscription_id=subscription.id,
                topic_id=topic.id if topic else None,
                provider=self.discovery_provider.name,
                query=query,
                from_publication_date=start_date,
                until_publication_date=end_date,
            )
            try:
                search_started_at = perf_counter()
                search_result = self.discovery_provider.search(
                    DiscoverySearchRequest(
                        topic_query=query,
                        from_publication_date=start_date,
                        until_publication_date=end_date,
                        rows=rows,
                    )
                )
            except DiscoveryProviderError as error:
                log_event(
                    "discovery_provider_search_failed",
                    provider=self.discovery_provider.name,
                    subscription_id=subscription.id,
                    topic_id=topic.id if topic else None,
                    duration_ms=round(
                        (perf_counter() - search_started_at) * 1000,
                        2,
                    ),
                    error_type=type(error).__name__,
                )
                completed_run = self.discovery_repository.complete_discovery_run(
                    run.id,
                    status=DiscoveryRunStatus.FAILED,
                    error=str(error),
                )
                runs.append(completed_run)
                continue
            log_event(
                "discovery_provider_search_completed",
                provider=self.discovery_provider.name,
                subscription_id=subscription.id,
                topic_id=topic.id if topic else None,
                candidate_count=len(search_result.candidates),
                duration_ms=round((perf_counter() - search_started_at) * 1000, 2),
            )

            ranked_for_run = []
            for position, candidate in enumerate(search_result.candidates, start=1):
                stored_candidate = self._process_candidate(
                    run_id=run.id,
                    candidate=candidate,
                    rank_position=position,
                )
                ranked_for_run.append(stored_candidate)
                persisted_candidates.append(stored_candidate)

            completed_run = self.discovery_repository.complete_discovery_run(
                run.id,
                status=DiscoveryRunStatus.SUCCEEDED,
                error=None,
            )
            runs.append(completed_run)

        selected_papers = _select_digest_papers(
            candidates=tuple(persisted_candidates),
            minimum_relevance_score=subscription.minimum_relevance_score,
        )
        selected_papers = self._enrich_digest_papers(selected_papers)
        log_event(
            "digest_selection_completed",
            subscription_id=subscription.id,
            discovered_candidate_count=len(persisted_candidates),
            selected_paper_count=len(selected_papers),
            minimum_relevance_score=subscription.minimum_relevance_score,
        )
        title = f"{subscription.name} digest preview"
        plain_text = render_digest_plain_text(title=title, papers=selected_papers)
        html = render_digest_html(title=title, papers=selected_papers)
        digest_idempotency_key = (
            f"digest-preview:{subscription.id}:{start_date.isoformat()}:"
            f"{end_date.isoformat()}:{rows}"
        )
        digest = self.discovery_repository.add_digest(
            idempotency_key=digest_idempotency_key,
            subscription_id=subscription.id,
            topic_id=topics[0].id if topics else None,
            digest_date=end_date,
            period_start=start_date,
            period_end=end_date,
            status=DigestStatus.GENERATED,
            title=title,
            plain_text=plain_text,
            html=html,
            selected_papers=selected_papers,
            error=None,
        )
        delivery = self._deliver_digest(
            digest,
            destination=subscription.delivery_destination,
            idempotency_key=f"digest-preview:{digest.id}:{self.delivery_provider.name}",
        )

        return DigestRunResult(
            subscription=subscription,
            discovery_runs=tuple(runs),
            candidates=tuple(persisted_candidates),
            digest=digest,
            delivery=delivery,
        )

    def _enrich_digest_papers(
        self,
        papers: tuple[DigestPaper, ...],
    ) -> tuple[DigestPaper, ...]:
        """Add cached or newly generated LLM analysis summaries to digest papers."""

        if self.analysis_service is None:
            return papers

        return tuple(self._enrich_digest_paper(paper) for paper in papers)

    def _enrich_digest_paper(
        self,
        paper: DigestPaper,
    ) -> DigestPaper:
        """Return one digest paper with analysis-derived summary fields."""

        if self.analysis_service is None:
            return paper

        try:
            result = self.analysis_service.execute(paper.paper_id)
        except (PaperNotFoundError, NoAnalyzableContentError):
            return paper

        if result.outcome not in {
            PaperAnalysisOutcome.CREATED,
            PaperAnalysisOutcome.CACHED,
        }:
            return paper

        analysis = result.analysis.validated_analysis
        if analysis is None:
            return paper

        return _digest_paper_from_analysis(
            paper=paper,
            analysis=analysis,
            analysis_scope=result.analysis.analysis_scope.value,
        )

    def _deliver_digest(
        self,
        digest: StoredDigest,
        *,
        destination: str | None,
        idempotency_key: str,
        attempt_count: int = 1,
    ) -> StoredDigestDelivery:
        """Deliver one digest unless a successful delivery already exists."""

        existing_success = self.discovery_repository.get_successful_delivery(
            digest_id=digest.id,
            provider=self.delivery_provider.name,
        )
        if existing_success is not None:
            return existing_success

        delivery_started_at = perf_counter()
        delivery_result = self.delivery_provider.deliver(
            digest,
            destination=destination,
        )
        status = (
            DeliveryStatus.SUCCEEDED
            if delivery_result.succeeded
            else DeliveryStatus.FAILED
        )
        next_retry_at = (
            datetime.now(UTC) + timedelta(seconds=self.delivery_retry_delay_seconds)
            if status is DeliveryStatus.FAILED and delivery_result.retryable
            else None
        )
        log_event(
            "digest_delivery_completed",
            provider=delivery_result.provider,
            digest_id=digest.id,
            succeeded=delivery_result.succeeded,
            attempt_count=delivery_result.attempt_count,
            retryable=delivery_result.retryable,
            provider_response_id=delivery_result.provider_response_id,
            error_type="delivery_failed" if delivery_result.error else None,
            duration_ms=round((perf_counter() - delivery_started_at) * 1000, 2),
        )

        return self.discovery_repository.add_delivery(
            digest_id=digest.id,
            provider=delivery_result.provider,
            destination=delivery_result.destination,
            status=status,
            idempotency_key=idempotency_key,
            error=delivery_result.error,
            provider_response_id=delivery_result.provider_response_id,
            attempt_count=attempt_count,
            retryable=delivery_result.retryable,
            next_retry_at=next_retry_at,
        )

    def _process_candidate(
        self,
        *,
        run_id: int,
        candidate: DiscoveryCandidate,
        rank_position: int,
    ) -> StoredDiscoveryCandidate:
        """Deduplicate, ingest, score, and persist one candidate outcome."""

        normalized_doi = normalize_doi(candidate.doi) if candidate.doi else None
        normalized_title = normalize_title(candidate.title)
        duplicate = (
            self.discovery_repository.find_paper_by_doi(normalized_doi)
            if normalized_doi is not None
            else None
        )
        if duplicate is None and candidate.publication_date is not None:
            duplicate = self.discovery_repository.find_paper_by_title_year(
                normalized_title=normalized_title,
                publication_year=candidate.publication_date.year,
            )

        if duplicate is not None:
            paper = duplicate
            candidate_status = DiscoveryCandidateStatus.DUPLICATE
            outcome_reason = "Matched existing paper by DOI or conservative title-year."
        else:
            paper = self.discovery_repository.add_paper(
                NewPaper(
                    doi=candidate.doi,
                    normalized_doi=normalized_doi,
                    title=candidate.title,
                    normalized_title=normalized_title,
                    abstract=candidate.abstract,
                    journal=candidate.journal,
                    publication_date=candidate.publication_date,
                    source_url=candidate.source_url,
                    ingestion_source=candidate.provider_name,
                    provider_record_id=candidate.provider_record_id,
                )
            )
            candidate_status = DiscoveryCandidateStatus.INGESTED
            outcome_reason = "Created paper from discovery metadata."

        abstract_result = self.abstract_content_service.execute(
            paper.id,
            candidate.abstract or paper.abstract,
        )
        if abstract_result.content is not None:
            self.chunk_service.execute(abstract_result.content)

        relevance_score = None
        try:
            relevance = self.relevance_service.execute(paper.id)
            relevance_score = relevance.assessment.normalized_score
        except NoAnalyzableContentError:
            outcome_reason = "No analyzable abstract was available for scoring."

        return self.discovery_repository.add_discovery_candidate(
            run_id=run_id,
            candidate=candidate,
            normalized_doi=normalized_doi,
            normalized_title=normalized_title,
            status=candidate_status,
            paper_id=paper.id,
            relevance_score=relevance_score,
            rank_position=rank_position,
            outcome_reason=outcome_reason,
        )


def _combined_query(
    subscription_query: str,
    topic_query: str,
) -> str:
    """Combine subscription and topic queries."""

    return " ".join(
        part.strip() for part in (subscription_query, topic_query) if part.strip()
    )


def _select_digest_papers(
    *,
    candidates: tuple[StoredDiscoveryCandidate, ...],
    minimum_relevance_score: float,
) -> tuple[DigestPaper, ...]:
    """Select and rank digest papers from persisted candidates."""

    ranked = sorted(
        _deduplicate_digest_candidates(
            tuple(
                candidate
                for candidate in candidates
                if candidate.paper_id is not None
                and (candidate.relevance_score or 0.0) >= minimum_relevance_score
            )
        ),
        key=lambda item: (
            -(item.relevance_score or 0.0),
            item.title.casefold(),
            item.id,
        ),
    )

    return tuple(
        DigestPaper(
            paper_id=candidate.paper_id or 0,
            doi=candidate.normalized_doi,
            title=candidate.title,
            journal=None,
            publication_date=candidate.publication_date,
            relevance_score=candidate.relevance_score,
            analysis_scope="abstract_only"
            if candidate.relevance_score is not None
            else None,
            concise_summary=(
                "Candidate selected from provider metadata and deterministic relevance."
            ),
            methodology_highlights=("See paper abstract or full text when available.",),
            main_results=("Not summarized by LLM in digest preview.",),
            limitations=(
                "Digest preview is based on provider metadata and available "
                "extracted evidence.",
            ),
            link=(
                f"https://doi.org/{candidate.normalized_doi}"
                if candidate.normalized_doi is not None
                else None
            ),
            provenance=(
                f"Discovery provider {candidate.provider}; "
                f"outcome {candidate.status.value}."
            ),
            ranking_explanation=(
                f"Ranked by deterministic relevance score {candidate.relevance_score}."
            ),
        )
        for candidate in ranked[:10]
    )


def _deduplicate_digest_candidates(
    candidates: tuple[StoredDiscoveryCandidate, ...],
) -> tuple[StoredDiscoveryCandidate, ...]:
    """Keep the best-ranked candidate for each paper identity."""

    best_by_key: dict[tuple[str, object], StoredDiscoveryCandidate] = {}
    for candidate in candidates:
        key: tuple[str, object]
        if candidate.paper_id is not None:
            key = ("paper", candidate.paper_id)
        elif candidate.normalized_doi is not None:
            key = ("doi", candidate.normalized_doi)
        else:
            key = ("title", candidate.normalized_title)

        existing = best_by_key.get(key)
        if existing is None or _candidate_rank_key(candidate) < _candidate_rank_key(
            existing
        ):
            best_by_key[key] = candidate

    return tuple(best_by_key.values())


def _candidate_rank_key(
    candidate: StoredDiscoveryCandidate,
) -> tuple[float, str, int]:
    """Return an ascending sort key for candidate quality."""

    return (
        -(candidate.relevance_score or 0.0),
        candidate.title.casefold(),
        candidate.id,
    )


def _digest_paper_from_analysis(
    *,
    paper: DigestPaper,
    analysis: dict[str, Any],
    analysis_scope: str,
) -> DigestPaper:
    """Build digest summary fields from one validated paper analysis."""

    concise_summary = (
        _statement_text(analysis, "clinical_or_scientific_significance")
        or _statement_text(analysis, "objective")
        or paper.concise_summary
    )
    methodology_highlights = _first_non_empty(
        _statement_list(analysis, "methodology_steps", limit=3),
        _statement_values(
            analysis,
            (
                "study_design",
                "acquisition_details",
                "preprocessing",
                "model_or_statistical_methods",
                "validation_design",
                "comparison_methods",
            ),
            limit=3,
        ),
        paper.methodology_highlights,
    )
    main_results = _first_non_empty(
        _statement_list(analysis, "key_results", limit=3),
        _numerical_result_values(analysis, limit=3),
        paper.main_results,
    )
    limitations = _first_non_empty(
        _statement_list(analysis, "limitations", limit=3),
        _statement_list(analysis, "uncertainty", limit=2),
        ("No limitations were reported in the supplied evidence.",),
    )

    return DigestPaper(
        paper_id=paper.paper_id,
        doi=paper.doi,
        title=paper.title,
        journal=paper.journal,
        publication_date=paper.publication_date,
        relevance_score=paper.relevance_score,
        analysis_scope=analysis_scope,
        concise_summary=concise_summary,
        methodology_highlights=methodology_highlights,
        main_results=main_results,
        limitations=limitations,
        link=paper.link,
        provenance=f"{paper.provenance} LLM analysis summarized.",
        ranking_explanation=paper.ranking_explanation,
    )


def _first_non_empty(
    *values: tuple[str, ...],
) -> tuple[str, ...]:
    """Return the first non-empty tuple."""

    for value in values:
        if value:
            return value
    return ()


def _statement_values(
    analysis: dict[str, Any],
    field_names: tuple[str, ...],
    *,
    limit: int,
) -> tuple[str, ...]:
    """Return reportable texts from multiple statement fields."""

    values: list[str] = []
    for field_name in field_names:
        value = _statement_text(analysis, field_name)
        if value is not None:
            values.append(value)
        if len(values) >= limit:
            break

    return tuple(values)


def _statement_list(
    analysis: dict[str, Any],
    field_name: str,
    *,
    limit: int,
) -> tuple[str, ...]:
    """Return reportable texts from a list-valued statement field."""

    values = analysis.get(field_name)
    if not isinstance(values, list):
        return ()

    texts = [
        text
        for item in values
        if isinstance(item, dict)
        for text in (_text_if_reported(item),)
        if text is not None
    ]
    return tuple(texts[:limit])


def _statement_text(
    analysis: dict[str, Any],
    field_name: str,
) -> str | None:
    """Return one reportable text field from analysis JSON."""

    value = analysis.get(field_name)
    if not isinstance(value, dict):
        return None

    return _text_if_reported(value)


def _text_if_reported(
    statement: dict[str, Any],
) -> str | None:
    """Return statement text only when supplied evidence supports it."""

    if statement.get("status") not in {"reported", "uncertain"}:
        return None

    text = statement.get("text")
    return text if isinstance(text, str) and text.strip() else None


def _numerical_result_values(
    analysis: dict[str, Any],
    *,
    limit: int,
) -> tuple[str, ...]:
    """Return compact display strings for numerical results."""

    values = analysis.get("numerical_results")
    if not isinstance(values, list):
        return ()

    results: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        metric = value.get("metric")
        value_text = value.get("value_text")
        numeric_value = value.get("value")
        if not isinstance(metric, str):
            continue
        result_value = (
            value_text
            if isinstance(value_text, str)
            else str(numeric_value)
            if numeric_value is not None
            else None
        )
        if result_value is None:
            continue
        unit = value.get("unit")
        suffix = f" {unit}" if isinstance(unit, str) else ""
        results.append(f"{metric}: {result_value}{suffix}.")
        if len(results) >= limit:
            break

    return tuple(results)
