"""Unit tests for the location use cases (in-memory fakes, no DB)."""

from __future__ import annotations

from app.application.use_cases.get_location_history import GetLocationHistoryUseCase
from app.application.use_cases.record_location import RecordLocationCommand, RecordLocationUseCase
from app.domain.value_objects.coordinates import Coordinates
from tests.fakes import InMemoryLocationRepository


def _record(repo: InMemoryLocationRepository, user_id: int, lat: float) -> None:
    RecordLocationUseCase(repo).execute(
        RecordLocationCommand(user_id=user_id, location=Coordinates(latitude=lat, longitude=0))
    )


def test_record_location_persists_sample_with_id_and_timestamp() -> None:
    repo = InMemoryLocationRepository()
    sample = RecordLocationUseCase(repo).execute(
        RecordLocationCommand(user_id=1, location=Coordinates(latitude=17.385, longitude=78.486))
    )
    assert sample.id is not None
    assert sample.recorded_at is not None
    assert sample.location.latitude == 17.385


def test_history_returns_newest_first_page_and_total() -> None:
    repo = InMemoryLocationRepository()
    for lat in (1.0, 2.0, 3.0):  # recorded in this order
        _record(repo, user_id=1, lat=lat)

    page = GetLocationHistoryUseCase(repo).execute(1, limit=2, offset=0)

    assert page.total == 3
    # Newest first: the last recorded (lat=3.0) comes first.
    assert [s.location.latitude for s in page.items] == [3.0, 2.0]


def test_history_offset_returns_older_samples() -> None:
    repo = InMemoryLocationRepository()
    for lat in (1.0, 2.0, 3.0):
        _record(repo, user_id=1, lat=lat)

    page = GetLocationHistoryUseCase(repo).execute(1, limit=2, offset=2)
    assert [s.location.latitude for s in page.items] == [1.0]


def test_history_is_isolated_per_user() -> None:
    repo = InMemoryLocationRepository()
    _record(repo, user_id=1, lat=1.0)
    _record(repo, user_id=2, lat=2.0)

    page = GetLocationHistoryUseCase(repo).execute(1, limit=10, offset=0)
    assert page.total == 1
    assert page.items[0].location.latitude == 1.0
