"""Subscribers subcommand for Google Health CLI."""

from google_health_api.api import GoogleHealthApi
from google_health_api.model import Subscriber, SubscriberConfig

from ..utils import (
    execute_all_pages,
    get_json_payload,
    get_params_payload,
    print_error_json,
    print_json,
    serialize_response,
)
from ..validation import check_dry_run, validate_resource_name


async def handle_subscribers_cmd(args, api: GoogleHealthApi, pretty: bool) -> None:
    """Handle subscribers subcommands."""
    sub = args.subcommand
    if sub == "list":
        project = args.project
        limit = args.limit
        page_token = args.page_token

        params = get_params_payload(args)
        pageSize = params.get("pageSize", limit)
        pageToken = params.get("pageToken", page_token)

        result = await api.subscribers.list(
            project=project, page_size=pageSize, page_token=pageToken
        )
        if args.all:
            await execute_all_pages(args, result, None, pretty)
        else:
            print_json(serialize_response(result), pretty)

    elif sub == "create":
        payload = get_json_payload(args)
        subscriber_id = None
        if payload:
            endpoint_uri = payload.get("endpointUri")
            endpoint_auth = payload.get("endpointAuthorization", {})
            endpoint_secret = endpoint_auth.get("secret")
            configs = [
                SubscriberConfig.from_dict(c)
                for c in payload.get("subscriberConfigs", [])
            ]
        else:
            endpoint_uri = args.endpoint_uri
            endpoint_secret = args.endpoint_secret
            configs = []

        params = get_params_payload(args)
        subscriber_id = params.get("subscriberId", args.subscriber_id)

        if endpoint_uri is None or endpoint_secret is None:
            print_error_json(
                "Missing endpointUri or endpoint secret.", status="INVALID_ARGUMENT"
            )
        assert isinstance(endpoint_uri, str)
        assert isinstance(endpoint_secret, str)

        payload_dry = {
            "endpointUri": endpoint_uri,
            "endpointAuthorization": {"secret": endpoint_secret},
            "subscriberConfigs": [c.to_dict() for c in configs],
            "subscriberId": subscriber_id,
        }
        check_dry_run(
            args.dry_run, "POST", f"v4/projects/{args.project}/subscribers", payload_dry
        )

        result = await api.subscribers.create(
            project=args.project,
            endpoint_uri=endpoint_uri,
            endpoint_authorization_secret=endpoint_secret,
            subscriber_configs=configs if configs else None,
            subscriber_id=subscriber_id,
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

        sub_obj = Subscriber.from_dict(payload)
        result = await api.subscribers.patch(
            args.name, sub_obj, update_mask=update_mask
        )
        print_json(serialize_response(result), pretty)

    elif sub == "delete":
        validate_resource_name(args.name)
        params = get_params_payload(args)
        force = params.get("force", args.force)

        check_dry_run(args.dry_run, "DELETE", f"v4/{args.name}", {"force": force})
        result = await api.subscribers.delete(args.name, force=force)
        print_json(serialize_response(result), pretty)
