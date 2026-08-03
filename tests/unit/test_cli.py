from datetime import UTC, datetime, timedelta

from mrinsight.cli import _is_subscription_due
from mrinsight.discovery import DigestCadence, StoredSubscription


def _subscription(
    *,
    cadence: DigestCadence,
    enabled: bool = True,
    last_processed_at: datetime | None = None,
) -> StoredSubscription:
    return StoredSubscription(
        id=1,
        name="Scheduled digest",
        discovery_query="MRI CVR",
        topic_ids=(1,),
        minimum_relevance_score=0.0,
        preferred_categories=("mri", "cvr"),
        digest_cadence=cadence,
        enabled=enabled,
        last_processed_at=last_processed_at,
    )


def test_scheduler_treats_never_processed_enabled_subscription_as_due() -> None:
    now = datetime(2026, 8, 3, tzinfo=UTC)

    assert _is_subscription_due(
        _subscription(cadence=DigestCadence.WEEKLY),
        now,
    )


def test_scheduler_respects_cadence_interval() -> None:
    now = datetime(2026, 8, 3, tzinfo=UTC)

    assert _is_subscription_due(
        _subscription(
            cadence=DigestCadence.DAILY,
            last_processed_at=now - timedelta(days=1),
        ),
        now,
    )
    assert not _is_subscription_due(
        _subscription(
            cadence=DigestCadence.WEEKLY,
            last_processed_at=now - timedelta(days=6),
        ),
        now,
    )
    assert _is_subscription_due(
        _subscription(
            cadence=DigestCadence.MONTHLY,
            last_processed_at=now - timedelta(days=30),
        ),
        now,
    )


def test_scheduler_skips_manual_and_disabled_subscriptions() -> None:
    now = datetime(2026, 8, 3, tzinfo=UTC)

    assert not _is_subscription_due(
        _subscription(cadence=DigestCadence.MANUAL),
        now,
    )
    assert not _is_subscription_due(
        _subscription(cadence=DigestCadence.DAILY, enabled=False),
        now,
    )
