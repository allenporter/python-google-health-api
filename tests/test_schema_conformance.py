"""Tests to ensure Python models are conformant with the discovery JSON schema."""

import dataclasses
import json
import os
import types
from typing import Any, get_args, get_origin, Union

from google_health_api.model.activity import ObservationTimeInterval, Steps
from google_health_api.model.base import (
    Application,
    DailyRollupDataPoint,
    DataPoint,
    DataSource,
    Device,
    ReconciledDataPoint,
)
from google_health_api.model.device import PairedDevice
from google_health_api.model.health_metric import (
    HeartRate,
    HeartRateMetadata,
    ObservationSampleTime,
)
from google_health_api.model.profile import Date, Identity, IrnProfile, Profile
from google_health_api.model.settings import Settings
from google_health_api.model.subscription import (
    EndpointAuthorization,
    Subscriber,
    SubscriberConfig,
    Subscription,
)
from google_health_api.model.sleep import (
    Sleep,
    SessionTimeInterval,
    CivilDateTime,
    CivilTimeInterval,
    DailyRollUpDataPointsRequest,
    TimeOfDay,
    SleepStage,
    OutOfBedSegment,
    SleepSummary,
    StageSummary,
    SleepMetadata,
)
from google_health_api.model.activity import (
    Distance,
    BasalEnergyBurned,
    ActiveEnergyBurned,
    StepsRollupValue,
    DistanceRollupValue,
    ActiveEnergyBurnedRollupValue,
    TotalCaloriesRollupValue,
    Floors,
    FloorsRollupValue,
)
from google_health_api.model.health_metric import (
    VO2Max,
    Weight,
    DailyRestingHeartRate,
    DailyRestingHeartRateMetadata,
)
from google_health_api.model.hydration import (
    HydrationLog,
    HydrationLogRollupValue,
    VolumeQuantity,
    VolumeQuantityRollup,
)
from google_health_api.model.nutrition import (
    NutritionLog,
    NutritionLogRollupValue,
    WeightQuantity,
    EnergyQuantity,
    Serving,
    NutrientQuantity,
    WeightQuantityRollup,
    EnergyQuantityRollup,
    NutrientQuantityRollup,
)

# Mapping of Python classes to their corresponding schema names in the discovery document.
CLASS_TO_SCHEMA = {
    Steps: "Steps",
    ObservationTimeInterval: "ObservationTimeInterval",
    HeartRate: "HeartRate",
    ObservationSampleTime: "ObservationSampleTime",
    HeartRateMetadata: "HeartRateMetadata",
    Profile: "Profile",
    Date: "Date",
    Settings: "Settings",
    IrnProfile: "IrnProfile",
    Identity: "Identity",
    PairedDevice: "PairedDevice",
    Subscriber: "Subscriber",
    Subscription: "Subscription",
    EndpointAuthorization: "EndpointAuthorization",
    SubscriberConfig: "SubscriberConfig",
    DataSource: "DataSource",
    Device: "Device",
    Application: "Application",
    DataPoint: "DataPoint",
    ReconciledDataPoint: "ReconciledDataPoint",
    Sleep: "Sleep",
    SessionTimeInterval: "SessionTimeInterval",
    CivilDateTime: "CivilDateTime",
    TimeOfDay: "TimeOfDay",
    SleepStage: "SleepStage",
    OutOfBedSegment: "OutOfBedSegment",
    SleepSummary: "SleepSummary",
    StageSummary: "StageSummary",
    SleepMetadata: "SleepMetadata",
    Distance: "Distance",
    BasalEnergyBurned: "BasalEnergyBurned",
    VO2Max: "VO2Max",
    Weight: "Weight",
    ActiveEnergyBurned: "ActiveEnergyBurned",
    StepsRollupValue: "StepsRollupValue",
    DistanceRollupValue: "DistanceRollupValue",
    ActiveEnergyBurnedRollupValue: "ActiveEnergyBurnedRollupValue",
    TotalCaloriesRollupValue: "TotalCaloriesRollupValue",
    DailyRollupDataPoint: "DailyRollupDataPoint",
    CivilTimeInterval: "CivilTimeInterval",
    DailyRollUpDataPointsRequest: "DailyRollUpDataPointsRequest",
    Floors: "Floors",
    FloorsRollupValue: "FloorsRollupValue",
    VolumeQuantity: "VolumeQuantity",
    VolumeQuantityRollup: "VolumeQuantityRollup",
    HydrationLog: "HydrationLog",
    HydrationLogRollupValue: "HydrationLogRollupValue",
    DailyRestingHeartRate: "DailyRestingHeartRate",
    DailyRestingHeartRateMetadata: "DailyRestingHeartRateMetadata",
    WeightQuantity: "WeightQuantity",
    EnergyQuantity: "EnergyQuantity",
    Serving: "Serving",
    NutrientQuantity: "NutrientQuantity",
    NutritionLog: "NutritionLog",
    WeightQuantityRollup: "WeightQuantityRollup",
    EnergyQuantityRollup: "EnergyQuantityRollup",
    NutrientQuantityRollup: "NutrientQuantityRollup",
    NutritionLogRollupValue: "NutritionLogRollupValue",
}


def unwrap_type(t: Any) -> Any:
    """Unwrap Union types and retrieve the primary type (ignores None/NoneType)."""
    origin = get_origin(t)
    if origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType):
        args = get_args(t)
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return unwrap_type(non_none_args[0])
        return non_none_args
    return t


def get_field_alias(f: dataclasses.Field) -> str:
    """Get the serialization alias of a field, falling back to camelCase of the name."""
    if "alias" in f.metadata:
        return f.metadata["alias"]
    parts = f.name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def test_schema_conformance() -> None:
    """Verify that every field on our dataclasses matches the discovery schema properties and types."""
    # Find the discovery JSON file
    discovery_path = os.path.join(
        os.path.dirname(__file__), "..", "discovery", "health_v4_discovery.json"
    )
    assert os.path.exists(discovery_path), (
        f"Discovery file not found at {discovery_path}"
    )

    with open(discovery_path, "r") as f:
        discovery_doc = json.load(f)

    schemas = discovery_doc.get("schemas", {})
    assert schemas, "No schemas found in the discovery document"

    for cls, schema_name in CLASS_TO_SCHEMA.items():
        assert schema_name in schemas, (
            f"Schema {schema_name} not found in discovery document"
        )
        schema_def = schemas[schema_name]
        properties = schema_def.get("properties", {})

        # Ensure every field in the python class exists in the schema properties
        for field in dataclasses.fields(cls):
            if cls is DataPoint and field.name == "data":
                continue
            if cls is ReconciledDataPoint and field.name == "data_point":
                continue
            if cls is DailyRollupDataPoint and field.name == "data":
                continue

            alias = get_field_alias(field)
            assert alias in properties, (
                f"Field '{field.name}' (alias: '{alias}') on class {cls.__name__} "
                f"does not exist in schema '{schema_name}' properties: {list(properties.keys())}"
            )

            prop_def = properties[alias]
            field_type = unwrap_type(field.type)
            origin = get_origin(field_type)

            if origin is list:
                # Field is list[T]
                item_type = unwrap_type(get_args(field_type)[0])
                assert prop_def.get("type") == "array", (
                    f"Field '{field.name}' on {cls.__name__} is list, "
                    f"but schema property '{alias}' is not an array (type: {prop_def.get('type')})"
                )
                items_def = prop_def.get("items", {})

                if item_type in CLASS_TO_SCHEMA:
                    expected_ref = CLASS_TO_SCHEMA[item_type]
                    assert items_def.get("$ref") == expected_ref, (
                        f"Field '{field.name}' on {cls.__name__} has items of type {item_type.__name__}, "
                        f"but schema items $ref is {items_def.get('$ref')} (expected: {expected_ref})"
                    )
                else:
                    # Primitive array (e.g. list[str])
                    expected_type = "string" if item_type is str else None
                    assert items_def.get("type") == expected_type, (
                        f"Field '{field.name}' on {cls.__name__} has primitive items of type {item_type.__name__}, "
                        f"but schema items type is {items_def.get('type')} (expected: {expected_type})"
                    )
            elif field_type in CLASS_TO_SCHEMA:
                # Field is another nested dataclass
                expected_ref = CLASS_TO_SCHEMA[field_type]
                assert prop_def.get("$ref") == expected_ref, (
                    f"Field '{field.name}' on {cls.__name__} is nested class {field_type.__name__}, "
                    f"but schema property $ref is {prop_def.get('$ref')} (expected: {expected_ref})"
                )
            else:
                # Primitive type
                schema_type = prop_def.get("type")
                if field_type is str:
                    assert schema_type == "string", (
                        f"Field '{field.name}' on {cls.__name__} is str, "
                        f"but schema property type is {schema_type}"
                    )
                elif field_type is int:
                    # In discovery docs, large ints (int64) are often mapped as type: string, format: int64
                    assert schema_type in ("integer", "string"), (
                        f"Field '{field.name}' on {cls.__name__} is int, "
                        f"but schema property type is {schema_type}"
                    )
                elif field_type is float:
                    assert schema_type in ("number", "string"), (
                        f"Field '{field.name}' on {cls.__name__} is float, "
                        f"but schema property type is {schema_type}"
                    )
                elif field_type is bool:
                    assert schema_type == "boolean", (
                        f"Field '{field.name}' on {cls.__name__} is bool, "
                        f"but schema property type is {schema_type}"
                    )
