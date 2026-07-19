"""API client implementation for Google Health.

This module provides the main entry point for interacting with the Google Health API.
The primary class is `GoogleHealthApi`, which exposes namespaced sub-APIs for various
wearable data types (such as steps, sleep, distance, etc.), paired devices, and webhook subscribers.

Example usage:
```python
from google_health_api import GoogleHealthApi
from google_health_api.auth import ServiceAccountAuth

auth = ServiceAccountAuth("path/to/key.json")
api = GoogleHealthApi(auth)

# Fetch steps
steps_result = await api.steps.list()
for point in steps_result.data_points:
    print(
        f"Steps: {point.data.count} between {point.data.start_time} and {point.data.end_time}"
    )
```
"""

import re
from datetime import date, datetime, timezone, timedelta, tzinfo
from typing import Any, Generic, List, TypeVar
from zoneinfo import ZoneInfo

from mashumaro import DataClassDictMixin

from .auth import AbstractAuth
from .client import GoogleHealthSession
from .const import HealthApiScope
from .model import (
    ACTIVE_ENERGY_BURNED,
    BASAL_ENERGY_BURNED,
    DAILY_HEART_RATE_VARIABILITY,
    DAILY_RESTING_HEART_RATE,
    DISTANCE,
    FLOORS,
    HEART_RATE,
    HEART_RATE_VARIABILITY,
    HYDRATION_LOG,
    NUTRITION_LOG,
    SLEEP,
    STEPS,
    TOTAL_CALORIES,
    VO2_MAX,
    WEIGHT,
    HEIGHT,
    ALTITUDE,
    ACTIVE_MINUTES,
    ACTIVE_ZONE_MINUTES,
    SEDENTARY_PERIOD,
    SWIM_LENGTHS_DATA,
    ACTIVITY_LEVEL,
    TIME_IN_HEART_RATE_ZONE,
    CALORIES_IN_HEART_RATE_ZONE,
    BLOOD_GLUCOSE,
    CORE_BODY_TEMPERATURE,
    BODY_FAT,
    RUN_VO2_MAX,
    OXYGEN_SATURATION,
    DAILY_OXYGEN_SATURATION,
    EXERCISE,
    ELECTROCARDIOGRAM,
    IRREGULAR_RHYTHM_NOTIFICATION,
    DAILY_RESPIRATORY_RATE,
    RESPIRATORY_RATE_SLEEP_SUMMARY,
    DAILY_VO2_MAX,
    DAILY_HEART_RATE_ZONES,
    DAILY_SLEEP_TEMPERATURE_DERIVATIONS,
    ActiveEnergyBurned,
    BasalEnergyBurned,
    CivilDateTime,
    CivilTimeInterval,
    DailyRollUpDataPointsRequest,
    DailyRollupDataPoint,
    DailyRestingHeartRate,
    DailyHeartRateVariability,
    DataPoint,
    DataType,
    Date,
    Distance,
    Floors,
    HeartRate,
    HeartRateVariability,
    HydrationLog,
    NutritionLog,
    Identity,
    IrnProfile,
    ListPairedDevicesResult,
    ListDataPointResult,
    ListReconciledDataPointsResult,
    ListSubscribersResult,
    ListSubscriptionsResult,
    Operation,
    PairedDevice,
    Profile,
    ReconciledDataPoint,
    Settings,
    Sleep,
    Steps,
    Subscriber,
    SubscriberConfig,
    Subscription,
    UserInfo,
    VO2Max,
    Weight,
    Height,
    Bmi,
    Altitude,
    ActiveMinutes,
    ActiveZoneMinutes,
    SedentaryPeriod,
    SwimLengthsData,
    ActivityLevel,
    TimeInHeartRateZone,
    BloodGlucose,
    CoreBodyTemperature,
    BodyFat,
    RunVO2Max,
    OxygenSaturation,
    DailyOxygenSaturation,
    Exercise,
    Electrocardiogram,
    IrregularRhythmNotification,
    DailyRespiratoryRate,
    RespiratoryRateSleepSummary,
    DailyVO2Max,
    DailyHeartRateZones,
    DailySleepTemperatureDerivations,
    _ListDataPointsModel,
    _ListPairedDevicesModel,
    _ListReconciledDataPointsModel,
    _ListSubscribersModel,
    _ListSubscriptionsModel,
)

T = TypeVar("T", bound=DataClassDictMixin)

__all__ = [
    "GoogleHealthApi",
]


def _camel_to_snake(name: str) -> str:
    """Convert camelCase string to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _build_time_filter(
    time_field_path: str, start_time: datetime | None, end_time: datetime | None
) -> str | None:
    """Build an AIP-160 compatible time filter expression."""
    filters = []
    is_civil = "civil" in time_field_path
    is_date = time_field_path.endswith(".date")

    if start_time:
        if is_civil:
            iso_start = start_time.strftime("%Y-%m-%dT%H:%M:%S")
        elif is_date:
            iso_start = start_time.strftime("%Y-%m-%d")
        else:
            # Convert to UTC and format as ISO 8601 UTC string (z-normalized)
            utc_start = start_time.astimezone(timezone.utc)
            iso_start = utc_start.isoformat().replace("+00:00", "Z")
        filters.append(f'{time_field_path} >= "{iso_start}"')
    if end_time and "electrocardiogram" not in time_field_path:
        if is_civil:
            iso_end = end_time.strftime("%Y-%m-%dT%H:%M:%S")
        elif is_date:
            iso_end = end_time.strftime("%Y-%m-%d")
        else:
            # Convert to UTC and format as ISO 8601 UTC string (z-normalized)
            utc_end = end_time.astimezone(timezone.utc)
            iso_end = utc_end.isoformat().replace("+00:00", "Z")
        filters.append(f'{time_field_path} < "{iso_end}"')
    return " AND ".join(filters) if filters else None


class DataPointSubApi(Generic[T]):
    """Generic client providing namespaced operations for a specific DataType."""

    def __init__(self, session: GoogleHealthSession, data_type: DataType[T]) -> None:
        """Initialize the namespaced client."""
        self._session = session
        self._data_type = data_type

    @property
    def required_read_scopes(self) -> List[str]:
        """Return the list of scopes required to read from this API."""
        return self._data_type.read_scopes

    @property
    def required_write_scopes(self) -> List[str]:
        """Return the list of scopes required to write to this API."""
        return self._data_type.write_scopes

    async def list(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page_size: int = 100,
        page_token: str | None = None,
        user: str = "me",
    ) -> ListDataPointResult[T]:
        """List data points within an optional time range.

        Args:
            start_time: Retrieve data points after this timestamp.
            end_time: Retrieve data points before this timestamp.
            page_size: Maximum number of data points to return on a page.
            page_token: Page token to retrieve next set of records.
            user: User ID or literal 'me'.
        """

        async def fetch_page(token: str | None) -> _ListDataPointsModel[T]:
            params: dict[str, Any] = {"pageSize": page_size}
            if token:
                params["pageToken"] = token
            filter_expr = _build_time_filter(
                self._data_type.time_field_path, start_time, end_time
            )
            if filter_expr:
                params["filter"] = filter_expr

            resp = await self._session.get(
                f"v4/users/{user}/dataTypes/{self._data_type.key}/dataPoints",
                params=params,
            )
            raw_json = await resp.json()
            data_points = [
                DataPoint.from_api_dict(self._data_type, item)
                for item in raw_json.get("dataPoints", [])
            ]
            return _ListDataPointsModel(
                data_points=data_points,
                next_page_token=raw_json.get("nextPageToken"),
            )

        first_page = await fetch_page(page_token)
        return ListDataPointResult(first_page, fetch_page)

    async def reconcile(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page_size: int = 100,
        page_token: str | None = None,
        user: str = "me",
    ) -> ListReconciledDataPointsResult[T]:
        """Retrieve the reconciled stream of data points within a time range.

        Args:
            start_time: Retrieve data points after this timestamp.
            end_time: Retrieve data points before this timestamp.
            page_size: Maximum number of data points to return on a page.
            page_token: Page token to retrieve next set of records.
            user: User ID or literal 'me'.
        """

        async def fetch_page(token: str | None) -> _ListReconciledDataPointsModel[T]:
            params: dict[str, Any] = {"pageSize": page_size}
            if token:
                params["pageToken"] = token
            filter_expr = _build_time_filter(
                self._data_type.time_field_path, start_time, end_time
            )
            if filter_expr:
                params["filter"] = filter_expr

            resp = await self._session.get(
                f"v4/users/{user}/dataTypes/{self._data_type.key}/dataPoints:reconcile",
                params=params,
            )
            raw_json = await resp.json()
            reconciled_data_points = [
                ReconciledDataPoint.from_api_dict(self._data_type, item)
                for item in (
                    raw_json.get("dataPoints")
                    or raw_json.get("reconciledDataPoints")
                    or []
                )
            ]
            return _ListReconciledDataPointsModel(
                reconciled_data_points=reconciled_data_points,
                next_page_token=raw_json.get("nextPageToken"),
            )

        first_page = await fetch_page(page_token)
        return ListReconciledDataPointsResult(first_page, fetch_page)

    async def get(self, data_point_id: str, user: str = "me") -> DataPoint[T]:
        """Retrieve a specific data point.

        Args:
            data_point_id: The identifier of the data point.
            user: User ID or literal 'me'.
        """
        resp = await self._session.get(
            f"v4/users/{user}/dataTypes/{self._data_type.key}/dataPoints/{data_point_id}"
        )
        raw_json = await resp.json()
        return DataPoint.from_api_dict(self._data_type, raw_json)

    async def create(self, data_point: DataPoint[T], user: str = "me") -> DataPoint[T]:
        """Create a new data point.

        Args:
            data_point: The DataPoint object containing metadata and data.
            user: User ID or literal 'me'.
        """
        payload: dict[str, Any] = {
            self._data_type.field_name: data_point.data.to_dict(),
        }
        if data_point.name:
            payload["name"] = data_point.name
        if data_point.data_source:
            payload["dataSource"] = data_point.data_source.to_dict()

        resp = await self._session.post(
            f"v4/users/{user}/dataTypes/{self._data_type.key}/dataPoints",
            json=payload,
        )
        raw_json = await resp.json()
        if "response" in raw_json:
            raw_json = raw_json["response"]
        return DataPoint.from_api_dict(self._data_type, raw_json)

    async def patch(
        self, data_point_id: str, data_point: DataPoint[T], user: str = "me"
    ) -> DataPoint[T]:
        """Update/patch an existing data point.

        Args:
            data_point_id: The identifier of the data point to modify.
            data_point: The DataPoint object containing updated values.
            user: User ID or literal 'me'.
        """
        payload: dict[str, Any] = {
            self._data_type.field_name: data_point.data.to_dict(),
        }
        if data_point.name:
            payload["name"] = data_point.name
        if data_point.data_source:
            payload["dataSource"] = data_point.data_source.to_dict()

        resp = await self._session.patch(
            f"v4/users/{user}/dataTypes/{self._data_type.key}/dataPoints/{data_point_id}",
            json=payload,
        )
        raw_json = await resp.json()
        if "response" in raw_json:
            raw_json = raw_json["response"]
        return DataPoint.from_api_dict(self._data_type, raw_json)

    async def delete(self, data_point_id: str, user: str = "me") -> None:
        """Delete an existing data point.

        Args:
            data_point_id: The identifier of the data point to delete.
            user: User ID or literal 'me'.
        """
        await self.batch_delete([data_point_id], user=user)

    async def batch_delete(self, data_point_ids: List[str], user: str = "me") -> None:
        """Batch delete multiple data points in a single request.

        Args:
            data_point_ids: List of data point IDs to delete.
            user: User ID or literal 'me'.
        """
        names = []
        for dp_id in data_point_ids:
            if "/" in dp_id:
                names.append(dp_id)
            else:
                names.append(
                    f"users/{user}/dataTypes/{self._data_type.key}/dataPoints/{dp_id}"
                )

        payload = {"names": names}
        await self._session.post(
            f"v4/users/{user}/dataTypes/{self._data_type.key}/dataPoints:batchDelete",
            json=payload,
        )


class RollupDataPointSubApi(DataPointSubApi[T]):
    """Generic client providing namespaced operations for a DataType that supports rollup."""

    async def daily_rollup(
        self,
        start_date: date,
        end_date: date,
        window_size_days: int = 1,
        user: str = "me",
    ) -> List[DailyRollupDataPoint[Any]]:
        """Fetch daily rollup values for this data type.

        Args:
            start_date: Start date of rollup (inclusive).
            end_date: End date of rollup (exclusive).
            window_size_days: Size of aggregation window.
            user: User ID or 'me'.
        """
        rollup_cls = self._data_type.rollup_cls
        if not rollup_cls:
            raise TypeError(
                f"DataType {self._data_type.key} does not support daily rollups."
            )

        start_dt = CivilDateTime(
            date=Date(year=start_date.year, month=start_date.month, day=start_date.day)
        )
        end_dt = CivilDateTime(
            date=Date(year=end_date.year, month=end_date.month, day=end_date.day)
        )
        interval = CivilTimeInterval(start=start_dt, end=end_dt)
        request_obj = DailyRollUpDataPointsRequest(
            range=interval,
            window_size_days=window_size_days,
        )

        resp = await self._session.post(
            f"v4/users/{user}/dataTypes/{self._data_type.key}/dataPoints:dailyRollUp",
            json=request_obj.to_dict(),
        )
        raw_json = await resp.json()
        rollup_points = [
            DailyRollupDataPoint.from_api_dict(
                rollup_cls,
                self._data_type.field_name,
                item,
            )
            for item in raw_json.get("rollupDataPoints", [])
        ]
        return rollup_points

    async def today(
        self,
        time_zone: tzinfo | str | None = None,
        user: str = "me",
    ) -> DailyRollupDataPoint[Any] | None:
        """Fetch today's rollup value for this data type.

        If time_zone is not provided, it will fetch the user's timezone from settings.
        """
        if not time_zone:
            time_zone = self._session._timezone_cache.get(user)
            if not time_zone:
                resp = await self._session.get(f"v4/users/{user}/settings")
                raw_json = await resp.json()
                time_zone = raw_json.get("timeZone", "UTC")
                self._session._timezone_cache[user] = time_zone

        if isinstance(time_zone, str):
            resolved_tz = ZoneInfo(time_zone)
        else:
            resolved_tz = time_zone

        now_local = datetime.now(resolved_tz)
        current_date = now_local.date()
        next_date = current_date + timedelta(days=1)

        rollups = await self.daily_rollup(
            start_date=current_date,
            end_date=next_date,
            user=user,
        )
        return rollups[0] if rollups else None

    async def yesterday(
        self,
        time_zone: tzinfo | str | None = None,
        user: str = "me",
    ) -> DailyRollupDataPoint[Any] | None:
        """Fetch yesterday's rollup value for this data type.

        If time_zone is not provided, it will fetch the user's timezone from settings.
        """
        if not time_zone:
            time_zone = self._session._timezone_cache.get(user)
            if not time_zone:
                resp = await self._session.get(f"v4/users/{user}/settings")
                raw_json = await resp.json()
                time_zone = raw_json.get("timeZone", "UTC")
                self._session._timezone_cache[user] = time_zone

        if isinstance(time_zone, str):
            resolved_tz = ZoneInfo(time_zone)
        else:
            resolved_tz = time_zone

        now_local = datetime.now(resolved_tz)
        current_date = now_local.date()
        yesterday_date = current_date - timedelta(days=1)

        rollups = await self.daily_rollup(
            start_date=yesterday_date,
            end_date=current_date,
            user=user,
        )
        return rollups[0] if rollups else None


class BmiSubApi:
    """Synthetic client providing Body Mass Index (BMI) calculated from height and weight."""

    def __init__(self, api: "GoogleHealthApi") -> None:
        """Initialize the namespaced client."""
        self._api = api

    @property
    def required_read_scopes(self) -> List[str]:
        """Return the list of scopes required to read from this API."""
        return [HealthApiScope.MEASUREMENTS_READ]

    @property
    def required_write_scopes(self) -> List[str]:
        """Return the list of scopes required to write to this API."""
        return []

    async def list(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page_size: int = 100,
        page_token: str | None = None,
        user: str = "me",
    ) -> ListDataPointResult[Bmi]:
        """List synthetic BMI data points within an optional time range.

        Args:
            start_time: Retrieve weight data points after this timestamp.
            end_time: Retrieve weight data points before this timestamp.
            page_size: Maximum number of weight data points to return.
            page_token: Page token to retrieve next set of records.
            user: User ID or literal 'me'.
        """
        # Fetch weight data points
        weight_result = await self._api.weight.list(
            start_time=start_time,
            end_time=end_time,
            page_size=page_size,
            page_token=page_token,
            user=user,
        )
        if not weight_result.data_points:
            return ListDataPointResult(_ListDataPointsModel())

        # Fetch height data points (since height is rarely updated, query all to cover possible records)
        height_result = await self._api.height.list(user=user)
        if not height_result.data_points:
            return ListDataPointResult(_ListDataPointsModel())

        # Sort heights by sample time
        heights = sorted(
            height_result.data_points,
            key=lambda dp: dp.data.sample_time.physical_time,
        )

        bmi_points = []
        for weight_dp in weight_result.data_points:
            w_time = weight_dp.data.sample_time.physical_time

            # Find the closest height record at or before the weight record
            best_height_dp = heights[0]
            for h_dp in heights:
                if h_dp.data.sample_time.physical_time <= w_time:
                    best_height_dp = h_dp
                else:
                    break

            w_g = weight_dp.data.weight_grams
            h_mm = best_height_dp.data.height_millimeters

            # BMI = weight_kg / height_m^2
            bmi_val = (w_g / 1000.0) / ((h_mm / 1000.0) ** 2)

            bmi_data = Bmi(
                bmi=round(bmi_val, 2),
                weight_grams=w_g,
                height_millimeters=h_mm,
                sample_time=weight_dp.data.sample_time,
            )

            # Construct DataPoint matching weight name/source but with bmi data
            new_name = (
                weight_dp.name.replace("weight", "bmi") if weight_dp.name else None
            )
            bmi_points.append(
                DataPoint(
                    name=new_name,
                    data=bmi_data,
                    data_source=weight_dp.data_source,
                )
            )

        model = _ListDataPointsModel(
            data_points=bmi_points,
            next_page_token=weight_result.next_page_token,
        )

        async def get_next_page(token: str) -> _ListDataPointsModel[Bmi]:
            next_result = await self.list(
                start_time=start_time,
                end_time=end_time,
                page_size=page_size,
                page_token=token,
                user=user,
            )
            return next_result._response

        return ListDataPointResult(
            model,
            get_next_page=get_next_page if weight_result.next_page_token else None,
        )


class PairedDevicesSubApi:
    """Client providing namespaced operations for PairedDevices."""

    def __init__(self, session: GoogleHealthSession) -> None:
        """Initialize the namespaced client."""
        self._session = session

    @property
    def required_read_scopes(self) -> List[str]:
        """Return the list of scopes required to read from this API."""
        return [HealthApiScope.SETTINGS_READ]

    @property
    def required_write_scopes(self) -> List[str]:
        """Return the list of scopes required to write to this API."""
        return []

    async def list(
        self,
        page_size: int = 100,
        page_token: str | None = None,
        user: str = "me",
    ) -> ListPairedDevicesResult:
        """List paired devices of the user.

        Args:
            page_size: Maximum number of devices to return.
            page_token: Page token to retrieve next set of records.
            user: User ID or literal 'me'.
        """

        async def fetch_page(token: str | None) -> _ListPairedDevicesModel:
            params: dict[str, Any] = {"pageSize": page_size}
            if token:
                params["pageToken"] = token

            resp = await self._session.get(
                f"v4/users/{user}/pairedDevices",
                params=params,
            )
            raw_json = await resp.json()
            return _ListPairedDevicesModel.from_dict(raw_json)

        first_page = await fetch_page(page_token)
        return ListPairedDevicesResult(first_page, fetch_page)

    async def get(self, device_id: str, user: str = "me") -> PairedDevice:
        """Retrieve a specific paired device.

        Args:
            device_id: The identifier of the paired device.
            user: User ID or literal 'me'.
        """
        resp = await self._session.get(f"v4/users/{user}/pairedDevices/{device_id}")
        raw_json = await resp.json()
        return PairedDevice.from_dict(raw_json)


def _normalize_project(project: str) -> str:
    """Normalize a project string to projects/{project} resource name format."""
    if not project.startswith("projects/"):
        return f"projects/{project}"
    return project


def _normalize_user(user: str) -> str:
    """Normalize a user string to users/{user} resource name format."""
    if not user.startswith("users/"):
        return f"users/{user}"
    return user


class SubscriptionsSubApi:
    """Client providing namespaced operations for subscriptions."""

    def __init__(self, session: GoogleHealthSession) -> None:
        """Initialize the subscriptions client."""
        self._session = session

    @property
    def required_read_scopes(self) -> List[str]:
        """Return the list of scopes required to read from this API."""
        return ["https://www.googleapis.com/auth/cloud-platform"]

    @property
    def required_write_scopes(self) -> List[str]:
        """Return the list of scopes required to write to this API."""
        return ["https://www.googleapis.com/auth/cloud-platform"]

    async def create(
        self,
        parent_subscriber: str,
        user: str,
        data_types: List[str] | None = None,
        subscription_id: str | None = None,
    ) -> Subscription:
        """Create a user subscription under a parent subscriber.

        Args:
            parent_subscriber: The parent subscriber resource name, e.g. "projects/my-project/subscribers/my-sub".
            user: The user ID or "users/me".
            data_types: List of data types to subscribe to (e.g. ["steps", "heart-rate"]).
            subscription_id: Optional user-provided ID for the subscription.
        """
        parent_path = _normalize_project(parent_subscriber)
        payload: dict[str, Any] = {
            "user": _normalize_user(user),
        }
        if data_types is not None:
            payload["dataTypes"] = data_types

        params = {}
        if subscription_id:
            params["subscriptionId"] = subscription_id

        resp = await self._session.post(
            f"v4/{parent_path}/subscriptions",
            json=payload,
            params=params,
        )
        raw_json = await resp.json()
        return Subscription.from_dict(raw_json)

    async def patch(
        self,
        name: str,
        subscription: Subscription,
        update_mask: str | None = None,
    ) -> Subscription:
        """Update a subscription's data types.

        Args:
            name: The full resource name of the subscription, e.g. "projects/my-project/subscribers/my-sub/subscriptions/my-subscription".
            subscription: The updated Subscription object.
            update_mask: Optional field mask specifying which fields to update.
        """
        params = {}
        if update_mask:
            params["updateMask"] = update_mask

        resp = await self._session.patch(
            f"v4/{name}",
            json=subscription.to_dict(),
            params=params,
        )
        raw_json = await resp.json()
        return Subscription.from_dict(raw_json)

    async def list(
        self,
        parent_subscriber: str,
        filter: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> ListSubscriptionsResult:
        """List subscriptions for a given parent subscriber.

        Args:
            parent_subscriber: The parent subscriber resource name, e.g. "projects/my-project/subscribers/my-sub".
            filter: Optional AIP-160 filter expression.
            page_size: Maximum number of subscriptions to return per page.
            page_token: Token to retrieve the next page of results.
        """
        parent_path = _normalize_project(parent_subscriber)

        async def fetch_page(token: str | None) -> _ListSubscriptionsModel:
            params: dict[str, Any] = {"pageSize": page_size}
            if filter:
                params["filter"] = filter
            if token:
                params["pageToken"] = token

            resp = await self._session.get(
                f"v4/{parent_path}/subscriptions",
                params=params,
            )
            raw_json = await resp.json()
            return _ListSubscriptionsModel.from_dict(raw_json)

        first_page = await fetch_page(page_token)
        return ListSubscriptionsResult(first_page, fetch_page)

    async def delete(self, name: str) -> None:
        """Delete a user subscription.

        Args:
            name: The full resource name of the subscription.
        """
        await self._session.delete(f"v4/{name}")


class SubscribersSubApi:
    """Client providing namespaced operations for subscribers."""

    subscriptions: SubscriptionsSubApi

    def __init__(self, session: GoogleHealthSession) -> None:
        """Initialize the subscribers client."""
        self._session = session
        self.subscriptions = SubscriptionsSubApi(session)

    @property
    def required_read_scopes(self) -> List[str]:
        """Return the list of scopes required to read from this API."""
        return ["https://www.googleapis.com/auth/cloud-platform"]

    @property
    def required_write_scopes(self) -> List[str]:
        """Return the list of scopes required to write to this API."""
        return ["https://www.googleapis.com/auth/cloud-platform"]

    async def create(
        self,
        project: str,
        endpoint_uri: str,
        endpoint_authorization_secret: str,
        subscriber_configs: List[SubscriberConfig] | None = None,
        subscriber_id: str | None = None,
    ) -> Operation:
        """Create a new subscriber endpoint.

        Args:
            project: Google Cloud project ID or "projects/my-project".
            endpoint_uri: The HTTPS URI where update notifications will be sent.
            endpoint_authorization_secret: The authorization secret for webhook notifications.
            subscriber_configs: Optional list of subscriber configurations.
            subscriber_id: Optional user-provided ID for the subscriber.
        """
        parent_path = _normalize_project(project)
        payload: dict[str, Any] = {
            "endpointUri": endpoint_uri,
            "endpointAuthorization": {
                "secret": endpoint_authorization_secret,
            },
        }
        if subscriber_configs is not None:
            payload["subscriberConfigs"] = [
                config.to_dict() for config in subscriber_configs
            ]

        params = {}
        if subscriber_id:
            params["subscriberId"] = subscriber_id

        resp = await self._session.post(
            f"v4/{parent_path}/subscribers",
            json=payload,
            params=params,
        )
        raw_json = await resp.json()
        return Operation.from_dict(raw_json)

    async def patch(
        self,
        name: str,
        subscriber: Subscriber,
        update_mask: str | None = None,
    ) -> Operation:
        """Update a subscriber endpoint configuration.

        Args:
            name: Full subscriber resource name, e.g. "projects/my-project/subscribers/my-sub".
            subscriber: The updated Subscriber object.
            update_mask: Optional field mask specifying which fields to update.
        """
        params = {}
        if update_mask:
            params["updateMask"] = update_mask

        resp = await self._session.patch(
            f"v4/{name}",
            json=subscriber.to_dict(),
            params=params,
        )
        raw_json = await resp.json()
        return Operation.from_dict(raw_json)

    async def list(
        self,
        project: str,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> ListSubscribersResult:
        """List subscribers under a project.

        Args:
            project: Google Cloud project ID or "projects/my-project".
            page_size: Maximum number of subscribers to return per page.
            page_token: Token to retrieve the next page of results.
        """
        parent_path = _normalize_project(project)

        async def fetch_page(token: str | None) -> _ListSubscribersModel:
            params: dict[str, Any] = {"pageSize": page_size}
            if token:
                params["pageToken"] = token

            resp = await self._session.get(
                f"v4/{parent_path}/subscribers",
                params=params,
            )
            raw_json = await resp.json()
            return _ListSubscribersModel.from_dict(raw_json)

        first_page = await fetch_page(page_token)
        return ListSubscribersResult(first_page, fetch_page)

    async def delete(self, name: str, force: bool = False) -> Operation:
        """Delete a subscriber registration.

        Args:
            name: Full subscriber resource name.
            force: If true, delete any child subscriptions as well.
        """
        params = {}
        if force:
            params["force"] = "true"

        resp = await self._session.delete(
            f"v4/{name}",
            params=params,
        )
        raw_json = await resp.json()
        return Operation.from_dict(raw_json)


class GoogleHealthApi:
    """The Google Health API client.

    This client serves as the main gateway to access all Google Health API resources.
    It exposes namespaced properties for specific data types, allowing you to list,
    get, create, patch, and delete data points in a type-safe manner.
    """

    steps: RollupDataPointSubApi[Steps]
    """Namespaced client for Step count data (`Steps` model)."""

    heart_rate: RollupDataPointSubApi[HeartRate]
    """Namespaced client for Heart rate data (`HeartRate` model)."""

    sleep: DataPointSubApi[Sleep]
    """Namespaced client for Sleep session data (`Sleep` model)."""

    distance: RollupDataPointSubApi[Distance]
    """Namespaced client for Distance traveled data (`Distance` model)."""

    basal_energy_burned: RollupDataPointSubApi[BasalEnergyBurned]
    """Namespaced client for Basal metabolic energy burned data (`BasalEnergyBurned` model)."""

    vo2_max: DataPointSubApi[VO2Max]
    """Namespaced client for VO2 Max fitness data (`VO2Max` model)."""

    weight: RollupDataPointSubApi[Weight]
    """Namespaced client for Body weight data (`Weight` model)."""

    height: DataPointSubApi[Height]
    """Namespaced client for Body height data (`Height` model)."""

    bmi: BmiSubApi
    """Namespaced client for synthetic Body Mass Index (BMI) data (`Bmi` model)."""

    active_energy_burned: RollupDataPointSubApi[ActiveEnergyBurned]
    """Namespaced client for Active energy burned data (`ActiveEnergyBurned` model)."""

    total_calories: RollupDataPointSubApi[Any]
    """Namespaced client for Total calories rollup data."""

    floors: RollupDataPointSubApi[Floors]
    """Namespaced client for Floors elevation data (`Floors` model)."""

    hydration_log: RollupDataPointSubApi[HydrationLog]
    """Namespaced client for Hydration log data (`HydrationLog` model)."""

    nutrition_log: RollupDataPointSubApi[NutritionLog]
    """Namespaced client for Nutrition log data (`NutritionLog` model)."""

    daily_resting_heart_rate: RollupDataPointSubApi[DailyRestingHeartRate]
    """Namespaced client for Daily resting heart rate data (`DailyRestingHeartRate` model)."""

    heart_rate_variability: DataPointSubApi[HeartRateVariability]
    """Namespaced client for Heart rate variability intraday data (`HeartRateVariability` model)."""

    daily_heart_rate_variability: RollupDataPointSubApi[DailyHeartRateVariability]
    """Namespaced client for Daily heart rate variability data (`DailyHeartRateVariability` model)."""

    oxygen_saturation: DataPointSubApi[OxygenSaturation]
    """Namespaced client for Oxygen saturation data (`OxygenSaturation` model)."""

    daily_oxygen_saturation: DataPointSubApi[DailyOxygenSaturation]
    """Namespaced client for Daily oxygen saturation data (`DailyOxygenSaturation` model)."""

    exercise: DataPointSubApi[Exercise]
    """Namespaced client for Exercise activity log data (`Exercise` model)."""

    electrocardiogram: DataPointSubApi[Electrocardiogram]
    """Namespaced client for Electrocardiogram data (`Electrocardiogram` model)."""

    irregular_rhythm_notification: DataPointSubApi[IrregularRhythmNotification]
    """Namespaced client for Irregular rhythm notification data (`IrregularRhythmNotification` model)."""

    daily_respiratory_rate: DataPointSubApi[DailyRespiratoryRate]
    """Namespaced client for Daily respiratory rate data (`DailyRespiratoryRate` model)."""

    respiratory_rate_sleep_summary: DataPointSubApi[RespiratoryRateSleepSummary]
    """Namespaced client for Respiratory rate sleep summary data (`RespiratoryRateSleepSummary` model)."""

    daily_vo2_max: DataPointSubApi[DailyVO2Max]
    """Namespaced client for Daily VO2 max data (`DailyVO2Max` model)."""

    daily_heart_rate_zones: DataPointSubApi[DailyHeartRateZones]
    """Namespaced client for Daily heart rate zones data (`DailyHeartRateZones` model)."""

    daily_sleep_temperature_derivations: DataPointSubApi[
        DailySleepTemperatureDerivations
    ]
    """Namespaced client for Daily sleep temperature derivations data (`DailySleepTemperatureDerivations` model)."""

    altitude: RollupDataPointSubApi[Altitude]
    """Namespaced client for Altitude gain delta data (`Altitude` model)."""

    body_fat: RollupDataPointSubApi[BodyFat]
    """Namespaced client for Body fat data (`BodyFat` model)."""

    active_minutes: RollupDataPointSubApi[ActiveMinutes]
    """Namespaced client for Active minutes data (`ActiveMinutes` model)."""

    active_zone_minutes: RollupDataPointSubApi[ActiveZoneMinutes]
    """Namespaced client for Active zone minutes data (`ActiveZoneMinutes` model)."""

    blood_glucose: RollupDataPointSubApi[BloodGlucose]
    """Namespaced client for Blood glucose data (`BloodGlucose` model)."""

    core_body_temperature: RollupDataPointSubApi[CoreBodyTemperature]
    """Namespaced client for Core body temperature data (`CoreBodyTemperature` model)."""

    sedentary_period: RollupDataPointSubApi[SedentaryPeriod]
    """Namespaced client for Sedentary period data (`SedentaryPeriod` model)."""

    swim_lengths_data: RollupDataPointSubApi[SwimLengthsData]
    """Namespaced client for Swim lengths data (`SwimLengthsData` model)."""

    run_vo2_max: RollupDataPointSubApi[RunVO2Max]
    """Namespaced client for Run VO2 Max data (`RunVO2Max` model)."""

    activity_level: RollupDataPointSubApi[ActivityLevel]
    """Namespaced client for Activity level data (`ActivityLevel` model)."""

    time_in_heart_rate_zone: RollupDataPointSubApi[TimeInHeartRateZone]
    """Namespaced client for Time in heart rate zone data (`TimeInHeartRateZone` model)."""

    calories_in_heart_rate_zone: RollupDataPointSubApi[Any]
    """Namespaced client for Calories in heart rate zone rollup data."""

    paired_devices: PairedDevicesSubApi
    """Namespaced client for managing user's paired devices."""

    subscribers: SubscribersSubApi
    """Namespaced client for managing webhook subscriber endpoints and subscriptions."""

    def __init__(self, auth: AbstractAuth) -> None:
        """Initialize the client."""
        self._session = GoogleHealthSession(auth, auth._websession, auth._host)
        self.steps = RollupDataPointSubApi(self._session, STEPS)
        self.heart_rate = RollupDataPointSubApi(self._session, HEART_RATE)
        self.sleep = DataPointSubApi(self._session, SLEEP)
        self.distance = RollupDataPointSubApi(self._session, DISTANCE)
        self.basal_energy_burned = RollupDataPointSubApi(
            self._session, BASAL_ENERGY_BURNED
        )
        self.vo2_max = DataPointSubApi(self._session, VO2_MAX)
        self.weight = RollupDataPointSubApi(self._session, WEIGHT)
        self.height = DataPointSubApi(self._session, HEIGHT)
        self.bmi = BmiSubApi(self)
        self.active_energy_burned = RollupDataPointSubApi(
            self._session, ACTIVE_ENERGY_BURNED
        )
        self.total_calories = RollupDataPointSubApi(self._session, TOTAL_CALORIES)
        self.floors = RollupDataPointSubApi(self._session, FLOORS)
        self.hydration_log = RollupDataPointSubApi(self._session, HYDRATION_LOG)
        self.nutrition_log = RollupDataPointSubApi(self._session, NUTRITION_LOG)
        self.daily_resting_heart_rate = RollupDataPointSubApi(
            self._session, DAILY_RESTING_HEART_RATE
        )
        self.heart_rate_variability = DataPointSubApi(
            self._session, HEART_RATE_VARIABILITY
        )
        self.daily_heart_rate_variability = RollupDataPointSubApi(
            self._session, DAILY_HEART_RATE_VARIABILITY
        )
        self.oxygen_saturation = DataPointSubApi(self._session, OXYGEN_SATURATION)
        self.daily_oxygen_saturation = DataPointSubApi(
            self._session, DAILY_OXYGEN_SATURATION
        )
        self.exercise = DataPointSubApi(self._session, EXERCISE)
        self.electrocardiogram = DataPointSubApi(self._session, ELECTROCARDIOGRAM)
        self.irregular_rhythm_notification = DataPointSubApi(
            self._session, IRREGULAR_RHYTHM_NOTIFICATION
        )
        self.daily_respiratory_rate = DataPointSubApi(
            self._session, DAILY_RESPIRATORY_RATE
        )
        self.respiratory_rate_sleep_summary = DataPointSubApi(
            self._session, RESPIRATORY_RATE_SLEEP_SUMMARY
        )
        self.daily_vo2_max = DataPointSubApi(self._session, DAILY_VO2_MAX)
        self.daily_heart_rate_zones = DataPointSubApi(
            self._session, DAILY_HEART_RATE_ZONES
        )
        self.daily_sleep_temperature_derivations = DataPointSubApi(
            self._session, DAILY_SLEEP_TEMPERATURE_DERIVATIONS
        )
        self.altitude = RollupDataPointSubApi(self._session, ALTITUDE)
        self.body_fat = RollupDataPointSubApi(self._session, BODY_FAT)
        self.active_minutes = RollupDataPointSubApi(self._session, ACTIVE_MINUTES)
        self.active_zone_minutes = RollupDataPointSubApi(
            self._session, ACTIVE_ZONE_MINUTES
        )
        self.blood_glucose = RollupDataPointSubApi(self._session, BLOOD_GLUCOSE)
        self.core_body_temperature = RollupDataPointSubApi(
            self._session, CORE_BODY_TEMPERATURE
        )
        self.sedentary_period = RollupDataPointSubApi(self._session, SEDENTARY_PERIOD)
        self.swim_lengths_data = RollupDataPointSubApi(self._session, SWIM_LENGTHS_DATA)
        self.run_vo2_max = RollupDataPointSubApi(self._session, RUN_VO2_MAX)
        self.activity_level = RollupDataPointSubApi(self._session, ACTIVITY_LEVEL)
        self.time_in_heart_rate_zone = RollupDataPointSubApi(
            self._session, TIME_IN_HEART_RATE_ZONE
        )
        self.calories_in_heart_rate_zone = RollupDataPointSubApi(
            self._session, CALORIES_IN_HEART_RATE_ZONE
        )
        self.paired_devices = PairedDevicesSubApi(self._session)
        self.subscribers = SubscribersSubApi(self._session)

    async def get_profile(self, user: str = "me") -> Profile:
        """Retrieve the user's profile details.

        Args:
            user: User ID or literal 'me'.
        """
        resp = await self._session.get(f"v4/users/{user}/profile")
        raw_json = await resp.json()
        return Profile.from_dict(raw_json)

    async def update_profile(
        self, profile: Profile, update_mask: str | None = None, user: str = "me"
    ) -> Profile:
        """Update the user's profile details.

        Args:
            profile: The updated Profile object.
            update_mask: Optional comma-separated list of fields to update.
            user: User ID or literal 'me'.
        """
        params = {}
        if update_mask:
            params["updateMask"] = update_mask

        resp = await self._session.patch(
            f"v4/users/{user}/profile",
            json=profile.to_dict(),
            params=params,
        )
        raw_json = await resp.json()
        return Profile.from_dict(raw_json)

    async def get_identity(self, user: str = "me") -> Identity:
        """Retrieve the user's identity mapping.

        Args:
            user: User ID or literal 'me'.
        """
        resp = await self._session.get(f"v4/users/{user}/identity")
        raw_json = await resp.json()
        return Identity.from_dict(raw_json)

    async def get_settings(self, user: str = "me") -> Settings:
        """Retrieve the user's settings.

        Args:
            user: User ID or literal 'me'.
        """
        resp = await self._session.get(f"v4/users/{user}/settings")
        raw_json = await resp.json()
        settings = Settings.from_dict(raw_json)
        if settings.time_zone:
            self._session._timezone_cache[user] = settings.time_zone
        return settings

    async def update_settings(
        self, settings: Settings, update_mask: str | None = None, user: str = "me"
    ) -> Settings:
        """Update the user's settings.

        Args:
            settings: The updated Settings object.
            update_mask: Optional comma-separated list of fields to update.
            user: User ID or literal 'me'.
        """
        params = {}
        if update_mask:
            params["updateMask"] = update_mask

        resp = await self._session.patch(
            f"v4/users/{user}/settings",
            json=settings.to_dict(),
            params=params,
        )
        raw_json = await resp.json()
        res_settings = Settings.from_dict(raw_json)
        if res_settings.time_zone:
            self._session._timezone_cache[user] = res_settings.time_zone
        else:
            self._session._timezone_cache.pop(user, None)
        return res_settings

    async def get_irn_profile(self, user: str = "me") -> IrnProfile:
        """Retrieve the user's Irregular Rhythm Notifications (IRN) profile details.

        Args:
            user: User ID or literal 'me'.
        """
        resp = await self._session.get(f"v4/users/{user}/irnProfile")
        raw_json = await resp.json()
        return IrnProfile.from_dict(raw_json)

    async def get_user_info(self) -> UserInfo:
        """Retrieve the authenticated user's Google OAuth2 userinfo."""
        resp = await self._session.get("https://www.googleapis.com/oauth2/v3/userinfo")
        raw_json = await resp.json()
        return UserInfo.from_dict(raw_json)
