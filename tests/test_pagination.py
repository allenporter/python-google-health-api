"""Tests for pagination models and async iteration."""

from unittest.mock import AsyncMock

import pytest

from google_health_api.model.pagination import (
    ListDataPointResult,
    ListReconciledDataPointsResult,
    _ListDataPointsModel,
    _ListReconciledDataPointsModel,
)


@pytest.mark.asyncio
async def test_list_data_point_result_single_page_no_token() -> None:
    """Test ListDataPointResult iteration with a single page and no next_page_token."""
    raw_page = _ListDataPointsModel(data_points=["dp1", "dp2"], next_page_token=None)  # type: ignore[arg-type]
    result = ListDataPointResult(raw_page)

    assert result.data_points == ["dp1", "dp2"]
    assert result.next_page_token is None

    pages = [page async for page in result]
    assert len(pages) == 1
    assert pages[0].data_points == ["dp1", "dp2"]


@pytest.mark.asyncio
async def test_list_data_point_result_single_page_no_get_next_page() -> None:
    """Test ListDataPointResult iteration when token exists but get_next_page is None."""
    raw_page = _ListDataPointsModel(data_points=["dp1"], next_page_token="token123")  # type: ignore[arg-type]
    result = ListDataPointResult(raw_page, get_next_page=None)

    assert result.next_page_token == "token123"

    pages = [page async for page in result]
    assert len(pages) == 1
    assert pages[0].data_points == ["dp1"]


@pytest.mark.asyncio
async def test_list_data_point_result_multi_page() -> None:
    """Test ListDataPointResult async iteration across multiple pages."""
    page1 = _ListDataPointsModel(
        data_points=["dp1", "dp2"], next_page_token="token_page_2"
    )  # type: ignore[arg-type]
    page2 = _ListDataPointsModel(
        data_points=["dp3", "dp4"], next_page_token="token_page_3"
    )  # type: ignore[arg-type]
    page3 = _ListDataPointsModel(data_points=["dp5"], next_page_token=None)  # type: ignore[arg-type]

    async def mock_get_next_page(token: str) -> _ListDataPointsModel:
        if token == "token_page_2":
            return page2
        if token == "token_page_3":
            return page3
        raise ValueError(f"Unexpected token: {token}")

    get_next_page_mock = AsyncMock(side_effect=mock_get_next_page)
    result = ListDataPointResult(page1, get_next_page=get_next_page_mock)

    pages = [page async for page in result]

    assert len(pages) == 3
    assert pages[0].data_points == ["dp1", "dp2"]
    assert pages[1].data_points == ["dp3", "dp4"]
    assert pages[2].data_points == ["dp5"]

    assert get_next_page_mock.call_count == 2
    get_next_page_mock.assert_any_call("token_page_2")
    get_next_page_mock.assert_any_call("token_page_3")


@pytest.mark.asyncio
async def test_list_reconciled_data_points_result_single_page_no_token() -> None:
    """Test ListReconciledDataPointsResult iteration with single page and no token."""
    raw_page = _ListReconciledDataPointsModel(
        reconciled_data_points=["rdp1"],
        next_page_token=None,  # type: ignore[arg-type]
    )
    result = ListReconciledDataPointsResult(raw_page)

    assert result.reconciled_data_points == ["rdp1"]
    assert result.next_page_token is None

    pages = [page async for page in result]
    assert len(pages) == 1
    assert pages[0].reconciled_data_points == ["rdp1"]


@pytest.mark.asyncio
async def test_list_reconciled_data_points_result_single_page_no_get_next_page() -> (
    None
):
    """Test ListReconciledDataPointsResult iteration when token exists but get_next_page is None."""
    raw_page = _ListReconciledDataPointsModel(
        reconciled_data_points=["rdp1"],
        next_page_token="token123",  # type: ignore[arg-type]
    )
    result = ListReconciledDataPointsResult(raw_page, get_next_page=None)

    assert result.next_page_token == "token123"

    pages = [page async for page in result]
    assert len(pages) == 1
    assert pages[0].reconciled_data_points == ["rdp1"]


@pytest.mark.asyncio
async def test_list_reconciled_data_points_result_multi_page() -> None:
    """Test ListReconciledDataPointsResult async iteration across multiple pages."""
    page1 = _ListReconciledDataPointsModel(
        reconciled_data_points=["rdp1"],
        next_page_token="token_page_2",  # type: ignore[arg-type]
    )
    page2 = _ListReconciledDataPointsModel(
        reconciled_data_points=["rdp2", "rdp3"],
        next_page_token=None,  # type: ignore[arg-type]
    )

    async def mock_get_next_page(token: str) -> _ListReconciledDataPointsModel:
        if token == "token_page_2":
            return page2
        raise ValueError(f"Unexpected token: {token}")

    get_next_page_mock = AsyncMock(side_effect=mock_get_next_page)
    result = ListReconciledDataPointsResult(page1, get_next_page=get_next_page_mock)

    pages = [page async for page in result]

    assert len(pages) == 2
    assert pages[0].reconciled_data_points == ["rdp1"]
    assert pages[1].reconciled_data_points == ["rdp2", "rdp3"]

    get_next_page_mock.assert_called_once_with("token_page_2")
