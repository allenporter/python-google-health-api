"""Dynamic schema introspection for Google Health CLI."""

import dataclasses
import typing
from typing import Any

from google_health_api.model import (
    Steps,
    HeartRate,
    Profile,
    Settings,
    Identity,
    IrnProfile,
    Subscriber,
    SubscriberConfig,
    Subscription,
    PairedDevice,
    DataSource,
)


def get_type_name(t: Any) -> str:
    """Return a string representation of a type."""
    import types

    origin = typing.get_origin(t)
    if origin is typing.Union or (
        hasattr(types, "UnionType") and origin is types.UnionType
    ):
        args = typing.get_args(t)
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return f"Optional[{get_type_name(non_none_args[0])}]"
        return " | ".join(get_type_name(a) for a in args)
    elif origin is list:
        args = typing.get_args(t)
        if args:
            return f"List[{get_type_name(args[0])}]"
        return "List"
    elif origin is dict:
        args = typing.get_args(t)
        if len(args) == 2:
            return f"Dict[{get_type_name(args[0])}, {get_type_name(args[1])}]"
        return "Dict"

    if hasattr(t, "__name__"):
        return t.__name__
    return str(t)


def generate_schema(cls: Any) -> dict[str, Any]:
    """Recursively generate a JSON schema description from a dataclass."""
    if not dataclasses.is_dataclass(cls):
        return {"type": get_type_name(cls)}

    schema: dict[str, Any] = {
        "type": "object",
        "description": cls.__doc__.strip() if cls.__doc__ else "",
        "properties": {},
    }

    for f in dataclasses.fields(cls):
        json_name = f.name
        if "field_options" in f.metadata:
            field_opts = f.metadata["field_options"]
            if hasattr(field_opts, "alias") and field_opts.alias:
                json_name = field_opts.alias
            elif isinstance(field_opts, dict) and "alias" in field_opts:
                json_name = field_opts["alias"]

        f_type = f.type
        origin = typing.get_origin(f_type)
        actual_type = f_type
        is_list = False

        if origin is typing.Union:
            args = typing.get_args(f_type)
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                actual_type = non_none[0]
                if typing.get_origin(actual_type) is list:
                    origin = list
                    args = typing.get_args(actual_type)
                    if args:
                        actual_type = args[0]

        if origin is list:
            is_list = True
            args = typing.get_args(f_type)
            if args:
                list_arg = args[0]
                if typing.get_origin(list_arg) is list:
                    list_args = typing.get_args(list_arg)
                    if list_args:
                        actual_type = list_args[0]
                else:
                    actual_type = list_arg

        if dataclasses.is_dataclass(actual_type):
            sub_schema = generate_schema(actual_type)
            if is_list:
                field_schema = {
                    "type": "array",
                    "items": sub_schema,
                    "description": f.metadata.get("description", "")
                    if f.metadata
                    else "",
                }
            else:
                field_schema = sub_schema
        else:
            field_schema = {
                "type": get_type_name(f_type),
                "description": f.metadata.get("description", "") if f.metadata else "",
            }

        schema["properties"][json_name] = field_schema

    return schema


def get_datapoint_schema(payload_cls: Any, payload_field: str) -> dict[str, Any]:
    """Generate the schema for a generic DataPoint with a specific payload class."""
    payload_schema = generate_schema(payload_cls)
    datasource_schema = generate_schema(DataSource)
    return {
        "type": "object",
        "properties": {
            "name": {
                "type": "Optional[str]",
                "description": "The unique resource path of the data point.",
            },
            "dataSource": datasource_schema,
            payload_field: payload_schema,
        },
    }


def get_command_schemas() -> dict[str, dict[str, Any]]:
    """Return request/response schemas for all CLI commands."""
    schemas = {
        "steps.list": {
            "description": "List step count data points within a time range.",
            "method": "GET",
            "endpoint": "v4/users/{user}/dataTypes/steps/dataPoints",
            "query_params": {
                "startTime": {
                    "type": "Optional[str]",
                    "description": "Filter start time as ISO 8601 UTC string.",
                },
                "endTime": {
                    "type": "Optional[str]",
                    "description": "Filter end time as ISO 8601 UTC string.",
                },
                "pageSize": {
                    "type": "Optional[int]",
                    "description": "Page size limit.",
                },
                "pageToken": {
                    "type": "Optional[str]",
                    "description": "Page token for next results page.",
                },
                "filter": {
                    "type": "Optional[str]",
                    "description": "AIP-160 compatible filter expression.",
                },
            },
            "response": {
                "type": "object",
                "properties": {
                    "dataPoints": {
                        "type": "array",
                        "items": get_datapoint_schema(Steps, "steps"),
                    },
                    "nextPageToken": {"type": "Optional[str]"},
                },
            },
        },
        "steps.get": {
            "description": "Retrieve a specific step count data point.",
            "method": "GET",
            "endpoint": "v4/users/{user}/dataTypes/steps/dataPoints/{data_point_id}",
            "response": get_datapoint_schema(Steps, "steps"),
        },
        "steps.create": {
            "description": "Create a new step count data point.",
            "method": "POST",
            "endpoint": "v4/users/{user}/dataTypes/steps/dataPoints",
            "request_body": get_datapoint_schema(Steps, "steps"),
            "response": get_datapoint_schema(Steps, "steps"),
        },
        "steps.patch": {
            "description": "Update/patch an existing step count data point.",
            "method": "PATCH",
            "endpoint": "v4/users/{user}/dataTypes/steps/dataPoints/{data_point_id}",
            "request_body": get_datapoint_schema(Steps, "steps"),
            "response": get_datapoint_schema(Steps, "steps"),
        },
        "steps.delete": {
            "description": "Delete a step count data point.",
            "method": "DELETE",
            "endpoint": "v4/users/{user}/dataTypes/steps/dataPoints/{data_point_id}",
            "response": {"type": "empty"},
        },
        "heart-rate.list": {
            "description": "List heart rate data points within a time range.",
            "method": "GET",
            "endpoint": "v4/users/{user}/dataTypes/heart-rate/dataPoints",
            "query_params": {
                "startTime": {"type": "Optional[str]"},
                "endTime": {"type": "Optional[str]"},
                "pageSize": {"type": "Optional[int]"},
                "pageToken": {"type": "Optional[str]"},
                "filter": {"type": "Optional[str]"},
            },
            "response": {
                "type": "object",
                "properties": {
                    "dataPoints": {
                        "type": "array",
                        "items": get_datapoint_schema(HeartRate, "heartRate"),
                    },
                    "nextPageToken": {"type": "Optional[str]"},
                },
            },
        },
        "heart-rate.get": {
            "description": "Retrieve a specific heart rate data point.",
            "method": "GET",
            "endpoint": "v4/users/{user}/dataTypes/heart-rate/dataPoints/{data_point_id}",
            "response": get_datapoint_schema(HeartRate, "heartRate"),
        },
        "heart-rate.create": {
            "description": "Create a new heart rate data point.",
            "method": "POST",
            "endpoint": "v4/users/{user}/dataTypes/heart-rate/dataPoints",
            "request_body": get_datapoint_schema(HeartRate, "heartRate"),
            "response": get_datapoint_schema(HeartRate, "heartRate"),
        },
        "heart-rate.patch": {
            "description": "Update/patch an existing heart rate data point.",
            "method": "PATCH",
            "endpoint": "v4/users/{user}/dataTypes/heart-rate/dataPoints/{data_point_id}",
            "request_body": get_datapoint_schema(HeartRate, "heartRate"),
            "response": get_datapoint_schema(HeartRate, "heartRate"),
        },
        "heart-rate.delete": {
            "description": "Delete a heart rate data point.",
            "method": "DELETE",
            "endpoint": "v4/users/{user}/dataTypes/heart-rate/dataPoints/{data_point_id}",
            "response": {"type": "empty"},
        },
        "profile.get": {
            "description": "Retrieve the user's profile details.",
            "method": "GET",
            "endpoint": "v4/users/{user}/profile",
            "response": generate_schema(Profile),
        },
        "profile.update": {
            "description": "Update the user's profile details.",
            "method": "PATCH",
            "endpoint": "v4/users/{user}/profile",
            "query_params": {
                "updateMask": {
                    "type": "Optional[str]",
                    "description": "Comma-separated list of fields to update.",
                }
            },
            "request_body": generate_schema(Profile),
            "response": generate_schema(Profile),
        },
        "settings.get": {
            "description": "Retrieve the user's settings.",
            "method": "GET",
            "endpoint": "v4/users/{user}/settings",
            "response": generate_schema(Settings),
        },
        "settings.update": {
            "description": "Update the user's settings.",
            "method": "PATCH",
            "endpoint": "v4/users/{user}/settings",
            "query_params": {
                "updateMask": {
                    "type": "Optional[str]",
                    "description": "Comma-separated list of fields to update.",
                }
            },
            "request_body": generate_schema(Settings),
            "response": generate_schema(Settings),
        },
        "devices.list": {
            "description": "List paired devices of the user.",
            "method": "GET",
            "endpoint": "v4/users/{user}/pairedDevices",
            "query_params": {
                "pageSize": {"type": "Optional[int]"},
                "pageToken": {"type": "Optional[str]"},
            },
            "response": {
                "type": "object",
                "properties": {
                    "pairedDevices": {
                        "type": "array",
                        "items": generate_schema(PairedDevice),
                    },
                    "nextPageToken": {"type": "Optional[str]"},
                },
            },
        },
        "devices.get": {
            "description": "Retrieve a specific paired device.",
            "method": "GET",
            "endpoint": "v4/users/{user}/pairedDevices/{device_id}",
            "response": generate_schema(PairedDevice),
        },
        "identity.get": {
            "description": "Retrieve user identity mapping.",
            "method": "GET",
            "endpoint": "v4/users/{user}/identity",
            "response": generate_schema(Identity),
        },
        "irn.get": {
            "description": "Retrieve user Irregular Rhythm Notification profile.",
            "method": "GET",
            "endpoint": "v4/users/{user}/irnProfile",
            "response": generate_schema(IrnProfile),
        },
        "subscribers.list": {
            "description": "List subscribers under a Google Cloud project.",
            "method": "GET",
            "endpoint": "v4/{project}/subscribers",
            "query_params": {
                "pageSize": {"type": "Optional[int]"},
                "pageToken": {"type": "Optional[str]"},
            },
            "response": {
                "type": "object",
                "properties": {
                    "subscribers": {
                        "type": "array",
                        "items": generate_schema(Subscriber),
                    },
                    "nextPageToken": {"type": "Optional[str]"},
                },
            },
        },
        "subscribers.create": {
            "description": "Create a new subscriber endpoint.",
            "method": "POST",
            "endpoint": "v4/{project}/subscribers",
            "query_params": {
                "subscriberId": {
                    "type": "Optional[str]",
                    "description": "User-provided subscriber ID.",
                }
            },
            "request_body": {
                "type": "object",
                "properties": {
                    "endpointUri": {"type": "str"},
                    "endpointAuthorization": {
                        "type": "object",
                        "properties": {"secret": {"type": "str"}},
                    },
                    "subscriberConfigs": {
                        "type": "Optional[array]",
                        "items": generate_schema(SubscriberConfig),
                    },
                },
            },
            "response": {
                "type": "object",
                "description": "Operation representing the status of the request.",
            },
        },
        "subscribers.patch": {
            "description": "Update a subscriber endpoint configuration.",
            "method": "PATCH",
            "endpoint": "v4/{name}",
            "query_params": {"updateMask": {"type": "Optional[str]"}},
            "request_body": generate_schema(Subscriber),
            "response": {
                "type": "object",
                "description": "Operation representing the status of the request.",
            },
        },
        "subscribers.delete": {
            "description": "Delete a subscriber registration.",
            "method": "DELETE",
            "endpoint": "v4/{name}",
            "query_params": {"force": {"type": "Optional[bool]"}},
            "response": {
                "type": "object",
                "description": "Operation representing the status of the request.",
            },
        },
        "subscriptions.list": {
            "description": "List subscriptions for a given parent subscriber.",
            "method": "GET",
            "endpoint": "v4/{parent_subscriber}/subscriptions",
            "query_params": {
                "filter": {"type": "Optional[str]"},
                "pageSize": {"type": "Optional[int]"},
                "pageToken": {"type": "Optional[str]"},
            },
            "response": {
                "type": "object",
                "properties": {
                    "subscriptions": {
                        "type": "array",
                        "items": generate_schema(Subscription),
                    },
                    "nextPageToken": {"type": "Optional[str]"},
                },
            },
        },
        "subscriptions.create": {
            "description": "Create a user subscription under a parent subscriber.",
            "method": "POST",
            "endpoint": "v4/{parent_subscriber}/subscriptions",
            "query_params": {"subscriptionId": {"type": "Optional[str]"}},
            "request_body": {
                "type": "object",
                "properties": {
                    "user": {"type": "str"},
                    "dataTypes": {"type": "Optional[List[str]]"},
                },
            },
            "response": generate_schema(Subscription),
        },
        "subscriptions.patch": {
            "description": "Update a subscription's data types.",
            "method": "PATCH",
            "endpoint": "v4/{name}",
            "query_params": {"updateMask": {"type": "Optional[str]"}},
            "request_body": generate_schema(Subscription),
            "response": generate_schema(Subscription),
        },
        "subscriptions.delete": {
            "description": "Delete a user subscription.",
            "method": "DELETE",
            "endpoint": "v4/{name}",
            "response": {"type": "empty"},
        },
    }
    return schemas
