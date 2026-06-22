"""Generic paginated response models for Google Health API."""

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Generic, Self, TypeVar

from .base import DataClassDictMixin, DataPoint, ReconciledDataPoint

T = TypeVar("T", bound=DataClassDictMixin)


@dataclass
class _ListDataPointsModel(Generic[T]):
    """Generic raw model representing a page of DataPoints."""

    data_points: list[DataPoint[T]] = field(default_factory=list)
    next_page_token: str | None = None


class ListDataPointResult(Generic[T]):
    """Response containing a list of data points and allowing paginated iteration."""

    def __init__(
        self,
        response: _ListDataPointsModel[T],
        get_next_page: (
            Callable[[str], Awaitable[_ListDataPointsModel[T]]] | None
        ) = None,
    ) -> None:
        """Initialize pagination result."""
        self._response = response
        self._get_next_page = get_next_page

    @property
    def data_points(self) -> list[DataPoint[T]]:
        """List of data points on this page."""
        return self._response.data_points

    @property
    def next_page_token(self) -> str | None:
        """Token to retrieve the next page."""
        return self._response.next_page_token

    async def __aiter__(self) -> AsyncIterator[Self]:
        """Async iterator to traverse through pages of responses."""
        response = self
        while response is not None:
            yield response
            if not response.next_page_token or not self._get_next_page:
                break
            page_result = await self._get_next_page(response.next_page_token)
            response = self.__class__(page_result, self._get_next_page)


@dataclass
class _ListReconciledDataPointsModel(Generic[T]):
    """Generic raw model representing a page of ReconciledDataPoints."""

    reconciled_data_points: list[ReconciledDataPoint[T]] = field(default_factory=list)
    next_page_token: str | None = None


class ListReconciledDataPointsResult(Generic[T]):
    """Response containing a list of reconciled data points and allowing pagination."""

    def __init__(
        self,
        response: _ListReconciledDataPointsModel[T],
        get_next_page: (
            Callable[[str], Awaitable[_ListReconciledDataPointsModel[T]]] | None
        ) = None,
    ) -> None:
        """Initialize pagination result."""
        self._response = response
        self._get_next_page = get_next_page

    @property
    def reconciled_data_points(self) -> list[ReconciledDataPoint[T]]:
        """List of reconciled data points on this page."""
        return self._response.reconciled_data_points

    @property
    def next_page_token(self) -> str | None:
        """Token to retrieve the next page."""
        return self._response.next_page_token

    async def __aiter__(self) -> AsyncIterator[Self]:
        """Async iterator to traverse through pages of responses."""
        response = self
        while response is not None:
            yield response
            if not response.next_page_token or not self._get_next_page:
                break
            page_result = await self._get_next_page(response.next_page_token)
            response = self.__class__(page_result, self._get_next_page)
