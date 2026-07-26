"""UserInfo subcommand for Google Health CLI."""

from google_health_api.api import GoogleHealthApi

from ..utils import print_json, serialize_response


async def handle_userinfo_cmd(args, api: GoogleHealthApi, pretty: bool) -> None:
    """Handle userinfo subcommands."""
    result = await api.get_user_info()
    print_json(serialize_response(result), pretty)
