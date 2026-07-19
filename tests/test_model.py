"""Tests for Google Health API data model registry and base types."""

from google_health_api import model
from google_health_api.model import DATATYPES


def test_datatype_mapping() -> None:
    """Test that DATATYPES resolves standard kebab-case keys to DataType objects."""
    assert DATATYPES.get("steps") is model.STEPS
    assert DATATYPES.get("weight") is model.WEIGHT
    assert DATATYPES.get("active-energy-burned") is model.ACTIVE_ENERGY_BURNED
