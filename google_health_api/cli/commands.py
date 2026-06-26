"""Command implementations for Google Health CLI."""

import asyncio
import contextvars
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, NoReturn
import aiohttp

from google_health_api.api import GoogleHealthApi
from google_health_api.auth import AbstractAuth
from google_health_api.client import GoogleHealthSession
from google_health_api.const import HealthApiScope, HEALTH_API_URL
from google_health_api.exceptions import HealthApiException
from google_health_api.model import (
    Profile,
    Settings,
    Subscriber,
    SubscriberConfig,
    Subscription,
    DataPoint,
    ReconciledDataPoint,
)

from .validation import validate_resource_name, check_dry_run

TOKEN_FILE = "token.json"
CLIENT_SECRET_FILE = "client_secret.json"
SCOPES = [
    HealthApiScope.ACTIVITY_READ,
    HealthApiScope.MEASUREMENTS_READ,
    HealthApiScope.PROFILE_READ,
    HealthApiScope.SETTINGS_READ,
]

fields_var = contextvars.ContextVar("fields", default=None)


class CliHealthSession(GoogleHealthSession):
    """Subclass of GoogleHealthSession to support dynamically injecting fields parameter."""

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        fields = fields_var.get()
        if fields:
            params = kwargs.setdefault("params", {})
            params["fields"] = fields
        return await super().request(method, url, headers=headers, **kwargs)


class CredentialsAuth(AbstractAuth):
    """Auth wrapper that uses google-auth credentials."""

    def __init__(
        self, websession: aiohttp.ClientSession, credentials, host: str | None = None
    ) -> None:
        super().__init__(websession, host)
        self._credentials = credentials

    async def async_get_access_token(self) -> str:
        if not self._credentials.valid:
            from google.auth.transport.requests import Request

            loop = asyncio.get_running_loop()
            req = Request()
            await loop.run_in_executor(None, self._credentials.refresh, req)
            save_credentials(self._credentials)
        return self._credentials.token


class EnvAuth(AbstractAuth):
    """Auth wrapper that uses environment variable token directly (Agent DX)."""

    def __init__(
        self, websession: aiohttp.ClientSession, token: str, host: str | None = None
    ) -> None:
        super().__init__(websession, host)
        self._token = token

    async def async_get_access_token(self) -> str:
        return self._token


def save_credentials(credentials) -> None:
    """Save credentials to local token file."""
    with open(TOKEN_FILE, "w") as f:
        f.write(credentials.to_json())


def load_credentials_or_env():
    """Load credentials from environment or token.json."""
    token_env = os.environ.get("GOOGLE_HEALTH_CLI_TOKEN")
    if token_env:
        return ("env", token_env)

    if not os.path.exists(TOKEN_FILE):
        return None

    from google.oauth2.credentials import Credentials

    with open(TOKEN_FILE, "r") as f:
        data = json.load(f)

    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=SCOPES,
    )
    return ("file", creds)


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
        res["dataSource"] = dp.data_source.to_dict()
    res[field_name] = dp.data.to_dict()
    return res


def serialize_reconciled_datapoint(
    rdp: ReconciledDataPoint, field_name: str
) -> dict[str, Any]:
    """Serialize generic ReconciledDataPoint class."""
    return {"dataPoint": serialize_datapoint(rdp.data_point, field_name)}


def serialize_response(result: Any, field_name: str | None = None) -> Any:
    """Serialize generic API result to JSON-compatible data structures."""
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if hasattr(result, "data_points"):
        assert field_name is not None
        return {
            "dataPoints": [
                serialize_datapoint(dp, field_name) for dp in result.data_points
            ],
            "nextPageToken": result.next_page_token,
        }
    if hasattr(result, "reconciled_data_points"):
        assert field_name is not None
        return {
            "reconciledDataPoints": [
                serialize_reconciled_datapoint(rdp, field_name)
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


def cmd_login(args) -> None:
    """Execute interactive OAuth login flow."""
    if not os.path.exists(CLIENT_SECRET_FILE):
        print_error_json(
            f"Client secrets file '{CLIENT_SECRET_FILE}' not found.",
            status="NOT_FOUND",
        )

    if not sys.stdin.isatty():
        print_error_json(
            "Cannot run interactive login in a headless environment.",
            status="FAILED_PRECONDITION",
        )

    import json

    with open(CLIENT_SECRET_FILE, "r") as f:
        client_secrets_data = json.load(f)

    is_web = "web" in client_secrets_data

    if is_web:
        from google_auth_oauthlib.flow import Flow

        redirect_uris = client_secrets_data["web"].get("redirect_uris", [])
        redirect_uri = redirect_uris[0] if redirect_uris else "http://localhost:8080/"

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )
        print("Web-based authentication flow:")
        print(f"URL: {authorization_url}")
        redirect_response = input("Redirected URL or auth code: ").strip()

        if not redirect_response:
            print_error_json(
                "Redirected URL cannot be empty.", status="INVALID_ARGUMENT"
            )

        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

        if "code=" in redirect_response or redirect_response.startswith("http"):
            flow.fetch_token(authorization_response=redirect_response)
        else:
            flow.fetch_token(code=redirect_response)
        credentials = flow.credentials
    else:
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
        )
        credentials = flow.run_local_server(port=0)

    save_credentials(credentials)
    print_json({"status": "SUCCESS", "message": "Logged in successfully."})


async def setup_client(session: aiohttp.ClientSession) -> GoogleHealthApi:
    """Setup GoogleHealthApi using active credentials."""
    auth_data = load_credentials_or_env()
    if not auth_data:
        print_error_json(
            "Not logged in. Set GOOGLE_HEALTH_CLI_TOKEN or run login first.",
            status="UNAUTHENTICATED",
        )

    host = os.environ.get("GOOGLE_HEALTH_API_URL") or HEALTH_API_URL
    if auth_data[0] == "env":
        auth = EnvAuth(session, auth_data[1], host=host)
    else:
        auth = CredentialsAuth(session, auth_data[1], host=host)

    api = GoogleHealthApi(auth)
    # Inject CliHealthSession
    api._session = CliHealthSession(auth, session, host)
    # Update nested api classes with the new session
    api.steps._session = api._session
    api.heart_rate._session = api._session
    api.paired_devices._session = api._session
    api.subscribers._session = api._session
    api.subscribers.subscriptions._session = api._session
    return api


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


def get_json_payload(args) -> dict[str, Any] | None:
    """Extract and parse the raw JSON payload from --json argument if present."""
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


async def handle_steps_cmd(args, api: GoogleHealthApi, pretty: bool) -> None:
    """Handle steps subcommands."""
    sub = args.subcommand
    if sub == "list":
        days = args.days
        limit = args.limit
        page_token = args.page_token
        start_time = None
        end_time = None

        params = get_params_payload(args)
        if "startTime" in params:
            start_time = datetime.fromisoformat(params["startTime"])
        else:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

        if "endTime" in params:
            end_time = datetime.fromisoformat(params["endTime"])

        pageSize = params.get("pageSize", limit)
        pageToken = params.get("pageToken", page_token)

        result = await api.steps.list(
            start_time=start_time,
            end_time=end_time,
            page_size=pageSize,
            page_token=pageToken,
        )
        if args.all:
            await execute_all_pages(args, result, "steps", pretty)
        else:
            print_json(serialize_response(result, "steps"), pretty)

    elif sub == "get":
        validate_resource_name(args.data_point_id)
        result = await api.steps.get(data_point_id=args.data_point_id)
        print_json(serialize_datapoint(result, "steps"), pretty)

    elif sub in ("create", "patch"):
        payload = get_json_payload(args)
        if payload is None:
            print_error_json(
                "Please provide raw JSON input using --json.", status="INVALID_ARGUMENT"
            )
        assert payload is not None

        # Dry run validation
        path = "v4/users/me/dataTypes/steps/dataPoints"
        if sub == "patch":
            validate_resource_name(args.data_point_id)
            path += f"/{args.data_point_id}"
        check_dry_run(
            args.dry_run, "POST" if sub == "create" else "PATCH", path, payload
        )

        from google_health_api.model.base import DataPoint

        # Deserialize payload steps
        dp = DataPoint.from_api_dict(api.steps._data_type, payload)
        if sub == "create":
            result = await api.steps.create(dp)
        else:
            result = await api.steps.patch(args.data_point_id, dp)
        print_json(serialize_datapoint(result, "steps"), pretty)

    elif sub == "delete":
        validate_resource_name(args.data_point_id)
        check_dry_run(
            args.dry_run,
            "DELETE",
            f"v4/users/me/dataTypes/steps/dataPoints/{args.data_point_id}",
        )
        await api.steps.delete(args.data_point_id)
        print_json(
            {
                "status": "SUCCESS",
                "message": f"Deleted steps point {args.data_point_id}",
            },
            pretty,
        )


async def handle_heart_rate_cmd(args, api: GoogleHealthApi, pretty: bool) -> None:
    """Handle heart rate subcommands."""
    sub = args.subcommand
    if sub == "list":
        days = args.days
        limit = args.limit
        page_token = args.page_token
        start_time = None
        end_time = None

        params = get_params_payload(args)
        if "startTime" in params:
            start_time = datetime.fromisoformat(params["startTime"])
        else:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)

        if "endTime" in params:
            end_time = datetime.fromisoformat(params["endTime"])

        pageSize = params.get("pageSize", limit)
        pageToken = params.get("pageToken", page_token)

        result = await api.heart_rate.list(
            start_time=start_time,
            end_time=end_time,
            page_size=pageSize,
            page_token=pageToken,
        )
        if args.all:
            await execute_all_pages(args, result, "heartRate", pretty)
        else:
            print_json(serialize_response(result, "heartRate"), pretty)

    elif sub == "get":
        validate_resource_name(args.data_point_id)
        result = await api.heart_rate.get(data_point_id=args.data_point_id)
        print_json(serialize_datapoint(result, "heartRate"), pretty)

    elif sub in ("create", "patch"):
        payload = get_json_payload(args)
        if payload is None:
            print_error_json(
                "Please provide raw JSON input using --json.", status="INVALID_ARGUMENT"
            )
        assert payload is not None

        path = "v4/users/me/dataTypes/heart-rate/dataPoints"
        if sub == "patch":
            validate_resource_name(args.data_point_id)
            path += f"/{args.data_point_id}"
        check_dry_run(
            args.dry_run, "POST" if sub == "create" else "PATCH", path, payload
        )

        from google_health_api.model.base import DataPoint

        dp = DataPoint.from_api_dict(api.heart_rate._data_type, payload)
        if sub == "create":
            result = await api.heart_rate.create(dp)
        else:
            result = await api.heart_rate.patch(args.data_point_id, dp)
        print_json(serialize_datapoint(result, "heartRate"), pretty)

    elif sub == "delete":
        validate_resource_name(args.data_point_id)
        check_dry_run(
            args.dry_run,
            "DELETE",
            f"v4/users/me/dataTypes/heart-rate/dataPoints/{args.data_point_id}",
        )
        await api.heart_rate.delete(args.data_point_id)
        print_json(
            {
                "status": "SUCCESS",
                "message": f"Deleted heart rate point {args.data_point_id}",
            },
            pretty,
        )


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


async def handle_settings_cmd(args, api: GoogleHealthApi, pretty: bool) -> None:
    """Handle settings subcommands."""
    sub = args.subcommand
    if sub == "get":
        result = await api.get_settings()
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
            "v4/users/me/settings",
            {"payload": payload, "updateMask": update_mask},
        )

        sett = Settings.from_dict(payload)
        result = await api.update_settings(sett, update_mask=update_mask)
        print_json(serialize_response(result), pretty)


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


async def async_run_cmd(args) -> None:
    """Async main routine that handles setup, context variables, and routing."""
    # Set fields context variable
    fields_var.set(args.fields)

    pretty = (args.output == "pretty" and sys.stdout.isatty()) or args.output == "json"

    async with aiohttp.ClientSession() as session:
        try:
            api = await setup_client(session)
            cmd = args.command
            if cmd == "steps":
                await handle_steps_cmd(args, api, pretty)
            elif cmd == "heart-rate":
                await handle_heart_rate_cmd(args, api, pretty)
            elif cmd == "profile":
                await handle_profile_cmd(args, api, pretty)
            elif cmd == "settings":
                await handle_settings_cmd(args, api, pretty)
            elif cmd == "devices":
                await handle_devices_cmd(args, api, pretty)
            elif cmd == "identity":
                await handle_identity_cmd(args, api, pretty)
            elif cmd == "irn":
                await handle_irn_cmd(args, api, pretty)
            elif cmd == "subscribers":
                await handle_subscribers_cmd(args, api, pretty)
            elif cmd == "subscriptions":
                await handle_subscriptions_cmd(args, api, pretty)
        except HealthApiException as err:
            print_error_json(str(err))
        except Exception as err:
            # Trap unexpected crashes to return standard JSON errors for agents
            print_error_json(f"Unexpected error: {err}")
