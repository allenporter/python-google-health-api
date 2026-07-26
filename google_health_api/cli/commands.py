"""Command implementations for Google Health CLI."""

import os
import sys
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import aiohttp

from google_health_api.api import GoogleHealthApi
from google_health_api.const import HEALTH_API_URL
from google_health_api.exceptions import HealthApiException
from google_health_api.model import DataPoint

from .auth import (
    CliHealthSession,
    CredentialsAuth,
    EnvAuth,
    fields_var,
    load_credentials_or_env,
)
from .subcommands.devices import handle_devices_cmd
from .subcommands.identity import handle_identity_cmd, handle_irn_cmd
from .subcommands.login import cmd_login  # noqa: F401
from .subcommands.profile import handle_profile_cmd
from .subcommands.settings import handle_settings_cmd
from .subcommands.subscribers import handle_subscribers_cmd
from .subcommands.subscriptions import handle_subscriptions_cmd
from .subcommands.userinfo import handle_userinfo_cmd
from .utils import (
    execute_all_pages,
    get_json_payload,
    get_params_payload,
    print_error_json,
    print_json,
    serialize_datapoint,
    serialize_response,
)
from .validation import check_dry_run, validate_resource_name

DATATYPE_COMMANDS = {
    "steps": ("steps", "steps", "steps"),
    "heart-rate": ("heart_rate", "heartRate", "heart rate"),
    "sleep": ("sleep", "sleep", "sleep"),
    "distance": ("distance", "distance", "distance"),
    "basal-energy-burned": (
        "basal_energy_burned",
        "basalEnergyBurned",
        "basal energy burned",
    ),
    "active-energy-burned": (
        "active_energy_burned",
        "activeEnergyBurned",
        "active energy burned",
    ),
    "total-calories": ("total_calories", "totalCalories", "total calories"),
    "vo2-max": ("vo2_max", "vo2Max", "VO2 max"),
    "weight": ("weight", "weight", "weight"),
    "height": ("height", "height", "height"),
    "bmi": ("bmi", "bmi", "BMI"),
    "exercise": ("exercise", "exercise", "exercise"),
    "daily-vo2-max": ("daily_vo2_max", "dailyVo2Max", "daily VO2 max"),
    "daily-heart-rate-zones": (
        "daily_heart_rate_zones",
        "dailyHeartRateZones",
        "daily heart rate zones",
    ),
    "daily-sleep-temperature-derivations": (
        "daily_sleep_temperature_derivations",
        "dailySleepTemperatureDerivations",
        "daily sleep temperature derivations",
    ),
    "daily-respiratory-rate": (
        "daily_respiratory_rate",
        "dailyRespiratoryRate",
        "daily respiratory rate",
    ),
    "respiratory-rate-sleep-summary": (
        "respiratory_rate_sleep_summary",
        "respiratoryRateSleepSummary",
        "respiratory rate sleep summary",
    ),
    "electrocardiogram": (
        "electrocardiogram",
        "electrocardiogram",
        "electrocardiogram",
    ),
    "irregular-rhythm-notification": (
        "irregular_rhythm_notification",
        "irregularRhythmNotification",
        "irregular rhythm notification",
    ),
    "oxygen-saturation": (
        "oxygen_saturation",
        "oxygenSaturation",
        "oxygen saturation",
    ),
    "daily-oxygen-saturation": (
        "daily_oxygen_saturation",
        "dailyOxygenSaturation",
        "daily oxygen saturation",
    ),
    "floors": ("floors", "floors", "floors"),
    "hydration-log": ("hydration_log", "hydrationLog", "hydration log"),
    "nutrition-log": ("nutrition_log", "nutritionLog", "nutrition log"),
    "daily-resting-heart-rate": (
        "daily_resting_heart_rate",
        "dailyRestingHeartRate",
        "daily resting heart rate",
    ),
    "heart-rate-variability": (
        "heart_rate_variability",
        "heartRateVariability",
        "heart rate variability",
    ),
    "daily-heart-rate-variability": (
        "daily_heart_rate_variability",
        "dailyHeartRateVariability",
        "daily heart rate variability",
    ),
    "altitude": ("altitude", "altitude", "altitude"),
    "body-fat": ("body_fat", "bodyFat", "body fat"),
    "active-minutes": ("active_minutes", "activeMinutes", "active minutes"),
    "active-zone-minutes": (
        "active_zone_minutes",
        "activeZoneMinutes",
        "active zone minutes",
    ),
    "blood-glucose": ("blood_glucose", "bloodGlucose", "blood glucose"),
    "core-body-temperature": (
        "core_body_temperature",
        "coreBodyTemperature",
        "core body temperature",
    ),
    "sedentary-period": ("sedentary_period", "sedentaryPeriod", "sedentary period"),
    "swim-lengths-data": (
        "swim_lengths_data",
        "swimLengthsData",
        "swim lengths data",
    ),
    "run-vo2-max": ("run_vo2_max", "runVo2Max", "run VO2 max"),
    "activity-level": ("activity_level", "activityLevel", "activity level"),
    "time-in-heart-rate-zone": (
        "time_in_heart_rate_zone",
        "timeInHeartRateZone",
        "time in heart rate zone",
    ),
    "calories-in-heart-rate-zone": (
        "calories_in_heart_rate_zone",
        "caloriesInHeartRateZone",
        "calories in heart rate zone",
    ),
}


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

    cli_session = CliHealthSession(
        auth,
        session,
        host,
        user_info_url=os.environ.get("GOOGLE_HEALTH_USERINFO_URL"),
    )
    return GoogleHealthApi(auth, session=cli_session)


async def handle_datatype_cmd(
    args,
    api: GoogleHealthApi,
    sub_api,
    field_name: str,
    key: str,
    display_name: str,
    pretty: bool,
) -> None:
    """Handle generic data type subcommands."""
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
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(days=days)

        if "endTime" in params:
            end_time = datetime.fromisoformat(params["endTime"])

        pageSize = params.get("pageSize", limit)
        pageToken = params.get("pageToken", page_token)

        result = await sub_api.list(
            start_time=start_time,
            end_time=end_time,
            page_size=pageSize,
            page_token=pageToken,
        )
        if args.all:
            await execute_all_pages(args, result, field_name, pretty)
        else:
            print_json(serialize_response(result, field_name), pretty)

    elif sub == "rollup":
        if not hasattr(sub_api, "daily_rollup"):
            print_error_json(
                f"DataType {key} does not support daily rollups.",
                status="INVALID_ARGUMENT",
            )
            return
        if args.start_date:
            start_date = date.fromisoformat(args.start_date)
            end_date = (
                date.fromisoformat(args.end_date)
                if args.end_date
                else start_date + timedelta(days=1)
            )
        else:
            timezone_str = args.timezone
            if not timezone_str:
                settings = await api.get_settings()
                timezone_str = settings.time_zone or "UTC"

            resolved_tz = ZoneInfo(timezone_str)
            now_local = datetime.now(resolved_tz)
            today = now_local.date()
            end_date = today + timedelta(days=1)
            start_date = end_date - timedelta(days=args.days)

        result = await sub_api.daily_rollup(
            start_date=start_date,
            end_date=end_date,
        )

        serialized = {
            "rollupDataPoints": [
                {
                    "civilStartTime": point.civil_start_time.to_dict()
                    if point.civil_start_time
                    else None,
                    "civilEndTime": point.civil_end_time.to_dict()
                    if point.civil_end_time
                    else None,
                    field_name: point.data.to_dict()
                    if hasattr(point.data, "to_dict")
                    else point.data,
                }
                for point in result
            ]
        }
        print_json(serialized, pretty)

    elif sub == "get":
        validate_resource_name(args.data_point_id)
        result = await sub_api.get(data_point_id=args.data_point_id)
        print_json(serialize_datapoint(result, field_name), pretty)

    elif sub in ("create", "patch"):
        payload = get_json_payload(args)
        if payload is None:
            print_error_json(
                "Please provide raw JSON input using --json.",
                status="INVALID_ARGUMENT",
            )
        assert payload is not None

        # Dry run validation
        path = f"v4/users/me/dataTypes/{key}/dataPoints"
        if sub == "patch":
            validate_resource_name(args.data_point_id)
            path += f"/{args.data_point_id}"
        check_dry_run(
            args.dry_run,
            "POST" if sub == "create" else "PATCH",
            path,
            payload,
        )

        dp = DataPoint.from_api_dict(sub_api.data_type, payload)
        if sub == "create":
            result = await sub_api.create(dp)
        else:
            result = await sub_api.patch(args.data_point_id, dp)
        print_json(serialize_datapoint(result, field_name), pretty)

    elif sub == "delete":
        validate_resource_name(args.data_point_id)
        check_dry_run(
            args.dry_run,
            "DELETE",
            f"v4/users/me/dataTypes/{key}/dataPoints/{args.data_point_id}",
        )
        await sub_api.delete(args.data_point_id)
        print_json(
            {
                "status": "SUCCESS",
                "message": f"Deleted {display_name} point {args.data_point_id}",
            },
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
            if cmd in DATATYPE_COMMANDS:
                api_attr, field_name, display_name = DATATYPE_COMMANDS[cmd]
                sub_api = getattr(api, api_attr)
                await handle_datatype_cmd(
                    args,
                    api,
                    sub_api,
                    field_name,
                    cmd,
                    display_name,
                    pretty,
                )
            elif cmd == "profile":
                await handle_profile_cmd(args, api, pretty)
            elif cmd == "userinfo":
                await handle_userinfo_cmd(args, api, pretty)
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
        except Exception as err:  # noqa: BLE001
            # Trap unexpected crashes to return standard JSON errors for agents
            print_error_json(f"Unexpected error: {err}")
