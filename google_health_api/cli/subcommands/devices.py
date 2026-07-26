"""Devices subcommand for Google Health CLI."""

from google_health_api.api import GoogleHealthApi

from ..utils import (
    execute_all_pages,
    get_params_payload,
    print_json,
    serialize_response,
)
from ..validation import validate_resource_name


async def handle_devices_cmd(args, api: GoogleHealthApi, pretty: bool) -> None:
    """Handle devices subcommands."""
    sub = args.subcommand
    if sub == "list":
        limit = args.limit
        page_token = args.page_token

        params = get_params_payload(args)
        pageSize = params.get("pageSize", limit)
        pageToken = params.get("pageToken", page_token)

        result = await api.paired_devices.list(page_size=pageSize, page_token=pageToken)
        if args.all:
            await execute_all_pages(args, result, None, pretty)
        else:
            print_json(serialize_response(result), pretty)
    elif sub == "get":
        validate_resource_name(args.device_id)
        result = await api.paired_devices.get(device_id=args.device_id)
        print_json(serialize_response(result), pretty)
