"""Subscriptions subcommand for Google Health CLI."""

from google_health_api.api import GoogleHealthApi
from google_health_api.model import Subscription

from ..utils import (
    execute_all_pages,
    get_json_payload,
    get_params_payload,
    print_error_json,
    print_json,
    serialize_response,
)
from ..validation import check_dry_run, validate_resource_name


async def handle_subscriptions_cmd(args, api: GoogleHealthApi, pretty: bool) -> None:
    """Handle subscriptions subcommands."""
    sub = args.subcommand
    if sub == "list":
        limit = args.limit
        page_token = args.page_token
        filter_expr = args.filter

        params = get_params_payload(args)
        pageSize = params.get("pageSize", limit)
        pageToken = params.get("pageToken", page_token)
        filter_str = params.get("filter", filter_expr)

        result = await api.subscribers.subscriptions.list(
            parent_subscriber=args.parent_subscriber,
            filter=filter_str,
            page_size=pageSize,
            page_token=pageToken,
        )
        if args.all:
            await execute_all_pages(args, result, None, pretty)
        else:
            print_json(serialize_response(result), pretty)

    elif sub == "create":
        payload = get_json_payload(args)
        subscription_id = None
        if payload:
            user = payload.get("user")
            data_types = payload.get("dataTypes")
        else:
            user = args.user
            data_types = args.data_types

        params = get_params_payload(args)
        subscription_id = params.get("subscriptionId", args.subscription_id)

        if user is None:
            print_error_json("Missing user parameter.", status="INVALID_ARGUMENT")
        assert isinstance(user, str)

        payload_dry = {
            "user": user,
            "dataTypes": data_types,
            "subscriptionId": subscription_id,
        }
        check_dry_run(
            args.dry_run,
            "POST",
            f"v4/{args.parent_subscriber}/subscriptions",
            payload_dry,
        )

        result = await api.subscribers.subscriptions.create(
            parent_subscriber=args.parent_subscriber,
            user=user,
            data_types=data_types,
            subscription_id=subscription_id,
        )
        print_json(serialize_response(result), pretty)

    elif sub == "patch":
        validate_resource_name(args.name)
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
            f"v4/{args.name}",
            {"payload": payload, "updateMask": update_mask},
        )

        sub_obj = Subscription.from_dict(payload)
        result = await api.subscribers.subscriptions.patch(
            args.name, sub_obj, update_mask=update_mask
        )
        print_json(serialize_response(result), pretty)

    elif sub == "delete":
        validate_resource_name(args.name)
        check_dry_run(args.dry_run, "DELETE", f"v4/{args.name}")
        await api.subscribers.subscriptions.delete(args.name)
        print_json(
            {"status": "SUCCESS", "message": f"Deleted subscription {args.name}"},
            pretty,
        )
