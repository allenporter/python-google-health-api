"""API client implementation for Google Health.

This module provides the main entry point for interacting with the Google Health API.
The primary class is `GoogleHealthApi`, which exposes namespaced sub-APIs for various
wearable data types (such as steps, sleep, distance, etc.), paired devices, and webhook subscribers.

Example usage:
    from google_health_api import GoogleHealthApi
    from google_health_api.auth import ServiceAccountAuth

    auth = ServiceAccountAuth("path/to/key.json")
    api = GoogleHealthApi(auth)

    # Fetch steps
    steps_result = await api.steps.list()
    for point in steps_result.data_points:
        print(f"Steps: {point.data.count} between {point.data.start_time} and {point.data.end_time}")
"""

import re
from datetime import datetime, timezone
from typing import Any, Generic, List, TypeVar

from mashumaro import DataClassDictMixin

from .auth import AbstractAuth
from .client import GoogleHealthSession
from .model import (
    BASAL_ENERGY_BURNED,
    DISTANCE,
    HEART_RATE,
    SLEEP,
    STEPS,
    VO2_MAX,
    WEIGHT,
    BasalEnergyBurned,
    DataPoint,
    DataType,
    Distance,
    HeartRate,
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
    VO2Max,
    Weight,
    _ListDataPointsModel,
    _ListPairedDevicesModel,
    _ListReconciledDataPointsModel,
    _ListSubscribersModel,
    _ListSubscriptionsModel,
)

T = TypeVar("T", bound=DataClassDictMixin)


def _camel_to_snake(name: str) -> str:
    """Convert camelCase string to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _build_time_filter(
    time_field_path: str, start_time: datetime | None, end_time: datetime | None
) -> str | None:
    """Build an AIP-160 compatible time filter expression."""
    filters = []
    if start_time:
        # Convert to UTC and format as ISO 8601 UTC string (z-normalized)
        utc_start = start_time.astimezone(timezone.utc)
        iso_start = utc_start.isoformat().replace("+00:00", "Z")
        filters.append(f'{time_field_path} >= "{iso_start}"')
    if end_time:
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
        return DataPoint.from_api_dict(self._data_type, raw_json)

    async def delete(self, data_point_id: str, user: str = "me") -> None:
        """Delete an existing data point.

        Args:
            data_point_id: The identifier of the data point to delete.
            user: User ID or literal 'me'.
        """
        await self._session.delete(
            f"v4/users/{user}/dataTypes/{self._data_type.key}/dataPoints/{data_point_id}"
        )

    async def batch_delete(self, data_point_ids: List[str], user: str = "me") -> None:
        """Batch delete multiple data points in a single request.

        Args:
            data_point_ids: List of data point IDs to delete.
            user: User ID or literal 'me'.
        """
        payload = {"dataPointIds": data_point_ids}
        await self._session.post(
            f"v4/users/{user}/dataTypes/{self._data_type.key}/dataPoints:batchDelete",
            json=payload,
        )


class PairedDevicesSubApi:
    """Client providing namespaced operations for PairedDevices."""

    def __init__(self, session: GoogleHealthSession) -> None:
        """Initialize the namespaced client."""
        self._session = session

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

    Attributes:
        steps: Namespaced client for Step count data (`Steps` model).
        heart_rate: Namespaced client for Heart rate data (`HeartRate` model).
        sleep: Namespaced client for Sleep session data (`Sleep` model).
        distance: Namespaced client for Distance traveled data (`Distance` model).
        basal_energy_burned: Namespaced client for Basal metabolic energy burned data (`BasalEnergyBurned` model).
        vo2_max: Namespaced client for VO2 Max fitness data (`VO2Max` model).
        weight: Namespaced client for Body weight data (`Weight` model).
        paired_devices: Namespaced client for managing user's paired devices.
        subscribers: Namespaced client for managing webhook subscriber endpoints and subscriptions.
    """

    steps: DataPointSubApi[Steps]
    """Namespaced client for Step count data (`Steps` model)."""

    heart_rate: DataPointSubApi[HeartRate]
    """Namespaced client for Heart rate data (`HeartRate` model)."""

    sleep: DataPointSubApi[Sleep]
    """Namespaced client for Sleep session data (`Sleep` model)."""

    distance: DataPointSubApi[Distance]
    """Namespaced client for Distance traveled data (`Distance` model)."""

    basal_energy_burned: DataPointSubApi[BasalEnergyBurned]
    """Namespaced client for Basal metabolic energy burned data (`BasalEnergyBurned` model)."""

    vo2_max: DataPointSubApi[VO2Max]
    """Namespaced client for VO2 Max fitness data (`VO2Max` model)."""

    weight: DataPointSubApi[Weight]
    """Namespaced client for Body weight data (`Weight` model)."""

    paired_devices: PairedDevicesSubApi
    """Namespaced client for managing user's paired devices."""

    subscribers: SubscribersSubApi
    """Namespaced client for managing webhook subscriber endpoints and subscriptions."""

    def __init__(self, auth: AbstractAuth) -> None:
        """Initialize the client."""
        self._session = GoogleHealthSession(auth, auth._websession, auth._host)
        self.steps = DataPointSubApi(self._session, STEPS)
        self.heart_rate = DataPointSubApi(self._session, HEART_RATE)
        self.sleep = DataPointSubApi(self._session, SLEEP)
        self.distance = DataPointSubApi(self._session, DISTANCE)
        self.basal_energy_burned = DataPointSubApi(self._session, BASAL_ENERGY_BURNED)
        self.vo2_max = DataPointSubApi(self._session, VO2_MAX)
        self.weight = DataPointSubApi(self._session, WEIGHT)
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
        return Settings.from_dict(raw_json)

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
        return Settings.from_dict(raw_json)

    async def get_irn_profile(self, user: str = "me") -> IrnProfile:
        """Retrieve the user's Irregular Rhythm Notifications (IRN) profile details.

        Args:
            user: User ID or literal 'me'.
        """
        resp = await self._session.get(f"v4/users/{user}/irnProfile")
        raw_json = await resp.json()
        return IrnProfile.from_dict(raw_json)
