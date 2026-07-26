"""Shared CLI utilities."""

import json
import sys
from typing import Any, NoReturn

from google_health_api.model import DataPoint, ReconciledDataPoint


def print_json(data: Any, pretty: bool = True) -> None:
    """Helper to output JSON data, respect pretty setting."""
    if pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data))


def print_error_json(message: str, status: str = "INTERNAL") -> NoReturn:
    """Print standard JSON error and exit."""
    res = {
        "error": {
            "status": status,
            "message": message,
        }
    }
    print_json(res)
    sys.exit(1)


def serialize_datapoint(dp: DataPoint, field_name: str) -> dict[str, Any]:
    """Serialize generic DataPoint class to dictionary matching API payload structure."""
    res: dict[str, Any] = {}
    if dp.name:
        res["name"] = dp.name
    if dp.data_source:
        res["dataSource"] = dp.data_source
    if hasattr(dp.data, "to_dict"):
        res[field_name] = dp.data.to_dict()
    else:
        res[field_name] = dp.data
    return res


def serialize_reconciled_datapoint(
    rdp: ReconciledDataPoint, field_name: str
) -> dict[str, Any]:
    """Serialize ReconciledDataPoint to dictionary structure."""
    return {"dataPoint": serialize_datapoint(rdp.data_point, field_name)}


def serialize_response(result: Any, field_name: str | None = None) -> Any:
    """Convert API response object/paginated result to JSON-serializable structure."""
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if hasattr(result, "data_points"):
        return {
            "dataPoints": [
                serialize_datapoint(dp, field_name or "")
                for dp in result.data_points
            ],
            "nextPageToken": result.next_page_token,
        }
    if hasattr(result, "reconciled_data_points"):
        return {
            "reconciledDataPoints": [
                serialize_reconciled_datapoint(rdp, field_name or "")
                for rdp in result.reconciled_data_points
            ],
            "nextPageToken": result.next_page_token,
        }
    if hasattr(result, "paired_devices"):
        return {
            "pairedDevices": [dev.to_dict() for dev in result.paired_devices],
            "nextPageToken": result.next_page_token,
        }
    if hasattr(result, "subscribers"):
        return {
            "subscribers": [sub.to_dict() for sub in result.subscribers],
            "nextPageToken": result.next_page_token,
        }
    if hasattr(result, "subscriptions"):
        return {
            "subscriptions": [sub.to_dict() for sub in result.subscriptions],
            "nextPageToken": result.next_page_token,
        }
    return result


def get_json_payload(args) -> dict[str, Any] | None:
    """Extract and parse raw JSON input payload if present."""
    if not hasattr(args, "json") or not args.json:
        return None
    try:
        return json.loads(args.json)
    except json.JSONDecodeError as err:
        print_error_json(f"Invalid raw JSON payload: {err}", status="INVALID_ARGUMENT")
    return None


def get_params_payload(args) -> dict[str, Any]:
    """Extract and parse --params query variables if present."""
    if not hasattr(args, "params") or not args.params:
        return {}
    try:
        return json.loads(args.params)
    except json.JSONDecodeError as err:
        print_error_json(
            f"Invalid --params JSON payload: {err}", status="INVALID_ARGUMENT"
        )
    return {}


async def execute_all_pages(
    args, result: Any, field_name: str | None, pretty: bool
) -> None:
    """Iterate and print items in NDJSON format for streaming output."""
    async for page in result:
        if hasattr(page, "data_points"):
            for item in page.data_points:
                assert field_name is not None
                print_json(serialize_datapoint(item, field_name), pretty=False)
        elif hasattr(page, "reconciled_data_points"):
            for item in page.reconciled_data_points:
                assert field_name is not None
                print_json(
                    serialize_reconciled_datapoint(item, field_name), pretty=False
                )
        elif hasattr(page, "paired_devices"):
            for item in page.paired_devices:
                print_json(item.to_dict(), pretty=False)
        elif hasattr(page, "subscribers"):
            for item in page.subscribers:
                print_json(item.to_dict(), pretty=False)
        elif hasattr(page, "subscriptions"):
            for item in page.subscriptions:
                print_json(item.to_dict(), pretty=False)
