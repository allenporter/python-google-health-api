"""Main CLI parser entrypoint for Google Health API CLI."""

import argparse
import asyncio
import sys

from .commands import cmd_login, async_run_cmd, print_json
from .schema import get_command_schemas


def cmd_schema(args) -> None:
    """Handle schema introspection command."""
    schemas = get_command_schemas()
    if args.command_name:
        if args.command_name in schemas:
            print_json(schemas[args.command_name])
        else:
            print(
                f"Unknown command for schema lookup: {args.command_name}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        # Print list of available commands
        list_schemas = {k: v.get("description", "") for k, v in schemas.items()}
        print_json(list_schemas)


def add_standard_datapoint_commands(
    subparsers, command_name: str, help_name: str, supports_rollup: bool = False
) -> None:
    """Helper to add standard list/get/create/patch/delete subparsers for a data type."""
    parser = subparsers.add_parser(command_name, help=f"Manage {help_name} data")
    sub_subparsers = parser.add_subparsers(dest="subcommand", required=True)

    lst = sub_subparsers.add_parser("list", help=f"List {help_name} data points")
    lst.add_argument(
        "--days", type=int, default=1, help="Number of days of history to fetch"
    )
    lst.add_argument(
        "--limit", type=int, default=10, help="Maximum number of records to fetch"
    )
    lst.add_argument(
        "--page-token",
        type=str,
        default=None,
        help="Token for the next page of results",
    )
    lst.add_argument(
        "--all",
        action="store_true",
        help="Auto-paginate and print all entries in NDJSON format",
    )

    gt = sub_subparsers.add_parser("get", help=f"Get a {help_name} data point")
    gt.add_argument("data_point_id", type=str, help="The data point identifier")

    sub_subparsers.add_parser("create", help=f"Create a new {help_name} data point")

    ptch = sub_subparsers.add_parser(
        "patch", help=f"Update/patch an existing {help_name} data point"
    )
    ptch.add_argument("data_point_id", type=str, help="The data point identifier")

    dl = sub_subparsers.add_parser("delete", help=f"Delete a {help_name} data point")
    dl.add_argument("data_point_id", type=str, help="The data point identifier")

    if supports_rollup:
        rl = sub_subparsers.add_parser("rollup", help=f"Roll up {help_name} data")
        rl.add_argument(
            "--timezone",
            type=str,
            default=None,
            help="Timezone for rollup (e.g. America/New_York). Defaults to settings timezone.",
        )
        rl.add_argument(
            "--days",
            type=int,
            default=1,
            help="Number of days to roll up. Defaults to 1 (today).",
        )
        rl.add_argument(
            "--start-date",
            type=str,
            default=None,
            help="Start date in YYYY-MM-DD format (inclusive).",
        )
        rl.add_argument(
            "--end-date",
            type=str,
            default=None,
            help="End date in YYYY-MM-DD format (exclusive).",
        )


def main() -> None:
    """CLI parser setup and subcommand routing."""
    parser = argparse.ArgumentParser(
        description="Google Health API CLI tool revamped with Agent DX principles."
    )
    # Global flags
    parser.add_argument(
        "--output",
        choices=["json", "pretty"],
        default="pretty",
        help="Specify the output formatting (default: pretty).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform validation locally without sending the request to the API.",
    )
    parser.add_argument(
        "--fields",
        type=str,
        default=None,
        help="A comma-separated list of fields to return (fields mask).",
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="Raw JSON payload for writing/updating operations.",
    )
    parser.add_argument(
        "--params",
        type=str,
        default=None,
        help="Raw JSON parameter mapping to bypass argument parsing for queries.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # login command
    subparsers.add_parser("login", help="Log in via browser and save credentials")

    # schema command
    schema_parser = subparsers.add_parser(
        "schema", help="Output request/response schema structures for operations"
    )
    schema_parser.add_argument(
        "command_name",
        type=str,
        nargs="?",
        default=None,
        help="The specific command to introspect (e.g. steps.create)",
    )

    # Register standard data type commands
    add_standard_datapoint_commands(
        subparsers, "steps", "step count", supports_rollup=True
    )
    add_standard_datapoint_commands(
        subparsers, "heart-rate", "heart rate", supports_rollup=False
    )
    add_standard_datapoint_commands(subparsers, "sleep", "sleep", supports_rollup=False)
    add_standard_datapoint_commands(
        subparsers, "distance", "distance", supports_rollup=True
    )
    add_standard_datapoint_commands(
        subparsers, "basal-energy-burned", "basal energy burned", supports_rollup=True
    )
    add_standard_datapoint_commands(
        subparsers, "vo2-max", "VO2 max", supports_rollup=False
    )
    add_standard_datapoint_commands(
        subparsers, "weight", "weight", supports_rollup=False
    )
    add_standard_datapoint_commands(
        subparsers, "active-energy-burned", "active energy burned", supports_rollup=True
    )
    add_standard_datapoint_commands(
        subparsers, "total-calories", "total calories", supports_rollup=True
    )
    add_standard_datapoint_commands(
        subparsers, "floors", "floors", supports_rollup=True
    )
    add_standard_datapoint_commands(
        subparsers, "hydration-log", "hydration log", supports_rollup=True
    )
    add_standard_datapoint_commands(
        subparsers, "nutrition-log", "nutrition log", supports_rollup=True
    )
    add_standard_datapoint_commands(
        subparsers,
        "daily-resting-heart-rate",
        "daily resting heart rate",
        supports_rollup=False,
    )

    # profile commands
    profile_parser = subparsers.add_parser(
        "profile", help="Manage user profile details"
    )
    profile_subparsers = profile_parser.add_subparsers(dest="subcommand", required=True)
    profile_subparsers.add_parser("get", help="Get user profile details")
    profile_update = profile_subparsers.add_parser(
        "update", help="Update user profile details"
    )
    profile_update.add_argument(
        "--update-mask",
        type=str,
        default=None,
        help="Comma-separated fields update mask",
    )

    # settings commands
    settings_parser = subparsers.add_parser("settings", help="Manage user settings")
    settings_subparsers = settings_parser.add_subparsers(
        dest="subcommand", required=True
    )
    settings_subparsers.add_parser("get", help="Get user settings")
    settings_update = settings_subparsers.add_parser(
        "update", help="Update user settings"
    )
    settings_update.add_argument(
        "--update-mask",
        type=str,
        default=None,
        help="Comma-separated fields update mask",
    )

    # paired devices commands
    devices_parser = subparsers.add_parser("devices", help="Manage paired devices")
    devices_subparsers = devices_parser.add_subparsers(dest="subcommand", required=True)
    devices_list = devices_subparsers.add_parser("list", help="List paired devices")
    devices_list.add_argument(
        "--limit", type=int, default=10, help="Maximum number of devices to return"
    )
    devices_list.add_argument(
        "--page-token",
        type=str,
        default=None,
        help="Token for the next page of results",
    )
    devices_list.add_argument(
        "--all",
        action="store_true",
        help="Auto-paginate and print all devices in NDJSON format",
    )
    devices_get = devices_subparsers.add_parser(
        "get", help="Get a specific paired device"
    )
    devices_get.add_argument("device_id", type=str, help="The paired device ID")

    # identity commands
    identity_parser = subparsers.add_parser("identity", help="Manage identity mapping")
    identity_subparsers = identity_parser.add_subparsers(
        dest="subcommand", required=True
    )
    identity_subparsers.add_parser("get", help="Get identity mapping details")

    # irn commands
    irn_parser = subparsers.add_parser("irn", help="Manage IRN profile")
    irn_subparsers = irn_parser.add_subparsers(dest="subcommand", required=True)
    irn_subparsers.add_parser("get", help="Get IRN profile details")

    # subscribers commands
    subscribers_parser = subparsers.add_parser("subscribers", help="Manage subscribers")
    subscribers_subparsers = subscribers_parser.add_subparsers(
        dest="subcommand", required=True
    )

    subscribers_list = subscribers_subparsers.add_parser(
        "list", help="List subscribers under a project"
    )
    subscribers_list.add_argument(
        "--project",
        type=str,
        default="me",
        help="Google Cloud project ID (default: me)",
    )
    subscribers_list.add_argument(
        "--limit", type=int, default=10, help="Maximum number of subscribers to return"
    )
    subscribers_list.add_argument(
        "--page-token",
        type=str,
        default=None,
        help="Token for the next page of results",
    )
    subscribers_list.add_argument(
        "--all",
        action="store_true",
        help="Auto-paginate and print all subscribers in NDJSON format",
    )

    subscribers_create = subscribers_subparsers.add_parser(
        "create", help="Create a subscriber endpoint"
    )
    subscribers_create.add_argument(
        "--project", type=str, default="me", help="Google Cloud project ID"
    )
    subscribers_create.add_argument(
        "--endpoint-uri", type=str, help="Webhook notifications destination URL"
    )
    subscribers_create.add_argument(
        "--endpoint-secret", type=str, help="Endpoint webhook authorization secret"
    )
    subscribers_create.add_argument(
        "--subscriber-id", type=str, help="Optional user-provided subscriber ID"
    )

    subscribers_patch = subscribers_subparsers.add_parser(
        "patch", help="Update a subscriber endpoint config"
    )
    subscribers_patch.add_argument(
        "name", type=str, help="The subscriber resource name"
    )
    subscribers_patch.add_argument(
        "--update-mask",
        type=str,
        default=None,
        help="Comma-separated fields update mask",
    )

    subscribers_delete = subscribers_subparsers.add_parser(
        "delete", help="Delete a subscriber registration"
    )
    subscribers_delete.add_argument(
        "name", type=str, help="The subscriber resource name"
    )
    subscribers_delete.add_argument(
        "--force",
        action="store_true",
        help="Force deletion of child subscriptions as well",
    )

    # subscriptions commands
    subscriptions_parser = subparsers.add_parser(
        "subscriptions", help="Manage subscriptions"
    )
    subscriptions_subparsers = subscriptions_parser.add_subparsers(
        dest="subcommand", required=True
    )

    subscriptions_list = subscriptions_subparsers.add_parser(
        "list", help="List subscriptions"
    )
    subscriptions_list.add_argument(
        "--parent-subscriber",
        type=str,
        required=True,
        help="Full subscriber resource name parent",
    )
    subscriptions_list.add_argument(
        "--filter", type=str, default=None, help="AIP-160 compatible filter expression"
    )
    subscriptions_list.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of subscriptions to return",
    )
    subscriptions_list.add_argument(
        "--page-token",
        type=str,
        default=None,
        help="Token for the next page of results",
    )
    subscriptions_list.add_argument(
        "--all",
        action="store_true",
        help="Auto-paginate and print all subscriptions in NDJSON format",
    )

    subscriptions_create = subscriptions_subparsers.add_parser(
        "create", help="Create a user subscription"
    )
    subscriptions_create.add_argument(
        "--parent-subscriber",
        type=str,
        required=True,
        help="Parent subscriber resource name",
    )
    subscriptions_create.add_argument(
        "--user", type=str, help="The target user path (e.g. users/me)"
    )
    subscriptions_create.add_argument(
        "--data-types",
        type=str,
        nargs="+",
        help="Data types list (e.g. steps heart-rate)",
    )
    subscriptions_create.add_argument(
        "--subscription-id", type=str, help="Optional user-provided subscription ID"
    )

    subscriptions_patch = subscriptions_subparsers.add_parser(
        "patch", help="Update a subscription's data types"
    )
    subscriptions_patch.add_argument(
        "name", type=str, help="The subscription resource name"
    )
    subscriptions_patch.add_argument(
        "--update-mask",
        type=str,
        default=None,
        help="Comma-separated fields update mask",
    )

    subscriptions_delete = subscriptions_subparsers.add_parser(
        "delete", help="Delete a user subscription"
    )
    subscriptions_delete.add_argument(
        "name", type=str, help="The subscription resource name"
    )

    args = parser.parse_args()

    if args.command == "login":
        cmd_login(args)
    elif args.command == "schema":
        cmd_schema(args)
    else:
        asyncio.run(async_run_cmd(args))


if __name__ == "__main__":
    main()
