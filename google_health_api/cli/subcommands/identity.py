"""Identity subcommands for Google Health CLI."""

from google_health_api.api import GoogleHealthApi

from ..utils import print_json, serialize_response


async def handle_identity_cmd(args, api: GoogleHealthApi, pretty: bool) -> None:
    """Handle identity subcommands."""
    if args.subcommand == "get":
        result = await api.get_identity()
        print_json(serialize_response(result), pretty)


async def handle_irn_cmd(args, api: GoogleHealthApi, pretty: bool) -> None:
    """Handle IRN subcommands."""
    if args.subcommand == "get":
        result = await api.get_irn_profile()
        print_json(serialize_response(result), pretty)
