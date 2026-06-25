"""Subscription and Subscriber models for Google Health API."""

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Self

from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig


@dataclass
class SubscriberConfig(DataClassDictMixin):
    """Configuration for a subscriber."""

    data_types: list[str] = field(
        metadata=field_options(alias="dataTypes"), default_factory=list
    )
    subscription_create_policy: str | None = field(
        metadata=field_options(alias="subscriptionCreatePolicy"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class EndpointAuthorization(DataClassDictMixin):
    """Authorization mechanism for a subscriber endpoint."""

    secret: str | None = None
    secret_set: bool | None = field(
        metadata=field_options(alias="secretSet"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class Subscriber(DataClassDictMixin):
    """A subscriber receiving notifications from Google Health API."""

    endpoint_uri: str = field(metadata=field_options(alias="endpointUri"))
    endpoint_authorization: EndpointAuthorization = field(
        metadata=field_options(alias="endpointAuthorization")
    )
    name: str | None = None
    state: str | None = None
    create_time: str | None = field(
        metadata=field_options(alias="createTime"), default=None
    )
    update_time: str | None = field(
        metadata=field_options(alias="updateTime"), default=None
    )
    subscriber_configs: list[SubscriberConfig] = field(
        metadata=field_options(alias="subscriberConfigs"), default_factory=list
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class Subscription(DataClassDictMixin):
    """A subscription to a data collection for a specific user."""

    user: str
    name: str | None = None
    data_types: list[str] = field(
        metadata=field_options(alias="dataTypes"), default_factory=list
    )

    class Config(BaseConfig):
        serialize_by_alias = True


@dataclass
class _ListSubscribersModel(DataClassDictMixin):
    """Raw model representing a page of Subscribers."""

    subscribers: list[Subscriber] = field(default_factory=list)
    next_page_token: str | None = field(
        metadata=field_options(alias="nextPageToken"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


class ListSubscribersResult:
    """Response containing a list of subscribers and allowing pagination."""

    def __init__(
        self,
        response: _ListSubscribersModel,
        get_next_page: (
            Callable[[str], Awaitable[_ListSubscribersModel]] | None
        ) = None,
    ) -> None:
        """Initialize pagination result."""
        self._response = response
        self._get_next_page = get_next_page

    @property
    def subscribers(self) -> list[Subscriber]:
        """List of subscribers on this page."""
        return self._response.subscribers

    @property
    def next_page_token(self) -> str | None:
        """Token to retrieve the next page."""
        return self._response.next_page_token

    async def __aiter__(self) -> AsyncIterator[Self]:
        """Async iterator to traverse through pages of subscribers."""
        response = self
        while response is not None:
            yield response
            if not response.next_page_token or not self._get_next_page:
                break
            page_result = await self._get_next_page(response.next_page_token)
            response = self.__class__(page_result, self._get_next_page)


@dataclass
class _ListSubscriptionsModel(DataClassDictMixin):
    """Raw model representing a page of Subscriptions."""

    subscriptions: list[Subscription] = field(default_factory=list)
    next_page_token: str | None = field(
        metadata=field_options(alias="nextPageToken"), default=None
    )

    class Config(BaseConfig):
        serialize_by_alias = True


class ListSubscriptionsResult:
    """Response containing a list of subscriptions and allowing pagination."""

    def __init__(
        self,
        response: _ListSubscriptionsModel,
        get_next_page: (
            Callable[[str], Awaitable[_ListSubscriptionsModel]] | None
        ) = None,
    ) -> None:
        """Initialize pagination result."""
        self._response = response
        self._get_next_page = get_next_page

    @property
    def subscriptions(self) -> list[Subscription]:
        """List of subscriptions on this page."""
        return self._response.subscriptions

    @property
    def next_page_token(self) -> str | None:
        """Token to retrieve the next page."""
        return self._response.next_page_token

    async def __aiter__(self) -> AsyncIterator[Self]:
        """Async iterator to traverse through pages of subscriptions."""
        response = self
        while response is not None:
            yield response
            if not response.next_page_token or not self._get_next_page:
                break
            page_result = await self._get_next_page(response.next_page_token)
            response = self.__class__(page_result, self._get_next_page)
