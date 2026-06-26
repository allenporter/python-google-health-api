"""Data models for Google Health API."""

from .activity import (
    BASAL_ENERGY_BURNED,
    DISTANCE,
    BasalEnergyBurned,
    Distance,
    STEPS,
    Steps,
)
from .base import DataPoint, DataSource, DataType, ReconciledDataPoint
from .device import ListPairedDevicesResult, PairedDevice, _ListPairedDevicesModel
from .health_metric import HEART_RATE, VO2_MAX, WEIGHT, HeartRate, VO2Max, Weight
from .pagination import (
    ListDataPointResult,
    ListReconciledDataPointsResult,
    _ListDataPointsModel,
    _ListReconciledDataPointsModel,
)
from .operation import Operation, Status
from .profile import Date, Identity, IrnProfile, Profile
from .settings import Settings
from .sleep import (
    SLEEP,
    CivilDateTime,
    OutOfBedSegment,
    SessionTimeInterval,
    Sleep,
    SleepMetadata,
    SleepStage,
    SleepSummary,
    StageSummary,
    TimeOfDay,
)
from .subscription import (
    EndpointAuthorization,
    ListSubscribersResult,
    ListSubscriptionsResult,
    Subscriber,
    SubscriberConfig,
    Subscription,
    _ListSubscribersModel,
    _ListSubscriptionsModel,
)

__all__ = [
    # --- Core & Base API Structures ---
    "DataType",
    "DataPoint",
    "ReconciledDataPoint",
    "DataSource",
    # --- Activity Models ---
    "Steps",
    "STEPS",
    "Distance",
    "DISTANCE",
    "BasalEnergyBurned",
    "BASAL_ENERGY_BURNED",
    # --- Health Metric Models ---
    "HeartRate",
    "HEART_RATE",
    "VO2Max",
    "VO2_MAX",
    "Weight",
    "WEIGHT",
    # --- Sleep Models ---
    "Sleep",
    "SLEEP",
    "SessionTimeInterval",
    "CivilDateTime",
    "TimeOfDay",
    "SleepStage",
    "OutOfBedSegment",
    "SleepSummary",
    "StageSummary",
    "SleepMetadata",
    # --- Profile & Settings Models ---
    "Profile",
    "IrnProfile",
    "Identity",
    "Settings",
    "Date",
    # --- Device & Webhook Subscription Models ---
    "PairedDevice",
    "Subscriber",
    "SubscriberConfig",
    "EndpointAuthorization",
    "Subscription",
    "Operation",
    "Status",
    # --- Pagination & Internal Result wrappers ---
    "ListDataPointResult",
    "ListReconciledDataPointsResult",
    "ListPairedDevicesResult",
    "ListSubscribersResult",
    "ListSubscriptionsResult",
    "_ListDataPointsModel",
    "_ListReconciledDataPointsModel",
    "_ListPairedDevicesModel",
    "_ListSubscribersModel",
    "_ListSubscriptionsModel",
]
