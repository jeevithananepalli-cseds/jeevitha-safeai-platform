"""Unit tests for the Coordinates domain value object.

Demonstrates that domain rules are testable with zero framework involvement.
"""

from __future__ import annotations

import dataclasses

import pytest

from app.domain.value_objects import Coordinates


def test_valid_coordinates_are_constructed() -> None:
    point = Coordinates(latitude=17.385044, longitude=78.486671)
    assert point.as_tuple() == (17.385044, 78.486671)


def test_boundary_values_are_accepted() -> None:
    Coordinates(latitude=90, longitude=180)
    Coordinates(latitude=-90, longitude=-180)


@pytest.mark.parametrize("latitude", [90.1, -90.1, 1000])
def test_out_of_range_latitude_is_rejected(latitude: float) -> None:
    with pytest.raises(ValueError, match="latitude"):
        Coordinates(latitude=latitude, longitude=0)


@pytest.mark.parametrize("longitude", [180.1, -180.1, 999])
def test_out_of_range_longitude_is_rejected(longitude: float) -> None:
    with pytest.raises(ValueError, match="longitude"):
        Coordinates(latitude=0, longitude=longitude)


def test_coordinates_are_immutable() -> None:
    point = Coordinates(latitude=0, longitude=0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        point.latitude = 10  # type: ignore[misc]
