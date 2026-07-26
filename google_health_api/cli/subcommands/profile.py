"""Profile subcommand for Google Health CLI."""

from google_health_api.api import GoogleHealthApi
from google_health_api.model import Profile

from ..utils import (
    get_json_payload,
    get_params_payload,
    print_error_json,
    print_json,
    serialize_response,
)
from ..validation import check_dry_run


async def handle_profile_cmd(args, api: GoogleHealthApi, pretty: bool) -> None:
    """Handle profile subcommands."""
    sub = args.subcommand
    if sub == "get":
        result = await api.get_profile()
        print_json(serialize_response(result), pretty)
    elif sub == "update":
        payload = get_json_payload(args)
        if payload is None:
            print_error_json(
                "Please provide raw JSON input using --json.", status="INVALID_ARGUMENT"
            )
        assert payload is not None

        params = get_params_payload(args)
        update_mask = params.get("updateMask", args.update_mask)

        check_dry_run(
            args.dry_run,
            "PATCH",
            "v4/users/me/profile",
            {"payload": payload, "updateMask": update_mask},
        )

        prof = Profile.from_dict(payload)
        result = await api.update_profile(prof, update_mask=update_mask)
        print_json(serialize_response(result), pretty)
