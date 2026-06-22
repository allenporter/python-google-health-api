"""API client implementation for Google Health."""

import re
from datetime import datetime, timezone
from typing import Any, Generic, List, TypeVar

from mashumaro import DataClassDictMixin

from .auth import AbstractAuth
from .client import GoogleHealthSession
from .model import (
    HEART_RATE,
    STEPS,
    DataPoint,
    DataType,
    HeartRate,
    ListDataPointResult,
    ListReconciledDataPointsResult,
    ReconciledDataPoint,
    Steps,
    _ListDataPointsModel,
    _ListReconciledDataPointsModel,
)

T = TypeVar("T", bound=DataClassDictMixin)


def _camel_to_snake(name: str) -> str:
    """Convert camelCase string to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _build_time_filter(
    field_name: str, start_time: datetime | None, end_time: datetime | None
) -> str | None:
    """Build an AIP-160 compatible time filter expression."""
    filters = []
    snake_field = _camel_to_snake(field_name)
    if start_time:
        # Convert to UTC and format as ISO 8601 UTC string (z-normalized)
        utc_start = start_time.astimezone(timezone.utc)
        iso_start = utc_start.isoformat().replace("+00:00", "Z")
        filters.append(f"{snake_field}.start_time > '{iso_start}'")
    if end_time:
        # Convert to UTC and format as ISO 8601 UTC string (z-normalized)
        utc_end = end_time.astimezone(timezone.utc)
        iso_end = utc_end.isoformat().replace("+00:00", "Z")
        filters.append(f"{snake_field}.end_time < '{iso_end}'")
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
                self._data_type.field_name, start_time, end_time
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
                self._data_type.field_name, start_time, end_time
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
                for item in raw_json.get("reconciledDataPoints", [])
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
            "data": {self._data_type.field_name: data_point.data.to_dict()},
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
            "data": {self._data_type.field_name: data_point.data.to_dict()},
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


class GoogleHealthApi:
    """The Google Health API client."""

    steps: DataPointSubApi[Steps]
    heart_rate: DataPointSubApi[HeartRate]

    def __init__(self, auth: AbstractAuth) -> None:
        """Initialize the client."""
        self._session = GoogleHealthSession(auth, auth._websession, auth._host)
        self.steps = DataPointSubApi(self._session, STEPS)
        self.heart_rate = DataPointSubApi(self._session, HEART_RATE)
