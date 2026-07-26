"""Unit tests for CLI schema introspection in google_health_api/cli/schema.py."""

import sys
import typing
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Dict, List, Optional, Union
from unittest.mock import patch

import pytest

from google_health_api.cli.main import main
from google_health_api.cli.schema import (
    generate_schema,
    get_command_schemas,
    get_datapoint_schema,
    get_datatype_schemas,
    get_type_name,
)
from google_health_api.model import Steps


def test_get_type_name_union_multi_non_none() -> None:
    """Test get_type_name with a Union having multiple non-None types."""
    res = get_type_name(Union[int, str])
    assert res == "int | str"


def test_get_type_name_bare_typing_list() -> None:
    """Test get_type_name with generic typing.List without type arguments (line 64)."""
    res = get_type_name(typing.List)
    assert res == "List"


def test_get_type_name_dict() -> None:
    """Test get_type_name with Dict[K, V] and bare typing.Dict (lines 66-69)."""
    res_parametrized = get_type_name(Dict[str, int])
    assert res_parametrized == "Dict[str, int]"

    res_bare = get_type_name(typing.Dict)
    assert res_bare == "Dict"


def test_get_type_name_no_name_attribute() -> None:
    """Test get_type_name with objects that do not have a __name__ attribute (line 73)."""

    class CustomObj:
        pass

    obj = CustomObj()
    res = get_type_name(obj)
    assert "CustomObj object" in res or str(obj) == res


def test_generate_schema_non_dataclass() -> None:
    """Test generate_schema with a non-dataclass type (line 79)."""
    res = generate_schema(int)
    assert res == {"type": "int"}

    res_str = generate_schema(str)
    assert res_str == {"type": "str"}


def test_generate_schema_field_alias_attr_and_dict() -> None:
    """Test generate_schema handles field_options with alias attribute and dict key (lines 90-94)."""

    @dataclass
    class ClassWithAttrAlias:
        normal_field: str
        aliased_field: int = field(
            metadata={"field_options": SimpleNamespace(alias="attr_alias_name")}
        )

    schema_attr = generate_schema(ClassWithAttrAlias)
    assert "attr_alias_name" in schema_attr["properties"]
    assert "aliased_field" not in schema_attr["properties"]

    @dataclass
    class ClassWithDictAlias:
        aliased_field: int = field(
            metadata={"field_options": {"alias": "dict_alias_name"}}
        )

    schema_dict = generate_schema(ClassWithDictAlias)
    assert "dict_alias_name" in schema_dict["properties"]
    assert "aliased_field" not in schema_dict["properties"]


def test_generate_schema_union_and_nested_list() -> None:
    """Test generate_schema handles Optional[List[Dataclass]] and List[List[Dataclass]] (lines 102-110, 118-120)."""

    @dataclass
    class SubItem:
        val: int

    @dataclass
    class ContainerUnion:
        items: Optional[List[SubItem]] = None

    schema_union = generate_schema(ContainerUnion)
    assert schema_union["properties"]["items"]["type"] == "array"
    assert (
        schema_union["properties"]["items"]["items"]["properties"]["val"]["type"]
        == "int"
    )

    @dataclass
    class ContainerNestedList:
        matrix: List[List[SubItem]]

    schema_nested = generate_schema(ContainerNestedList)
    assert schema_nested["properties"]["matrix"]["type"] == "array"
    assert (
        schema_nested["properties"]["matrix"]["items"]["properties"]["val"]["type"]
        == "int"
    )


def test_get_datapoint_schema() -> None:
    """Test get_datapoint_schema helper function."""
    schema = get_datapoint_schema(Steps, "steps")
    assert schema["type"] == "object"
    assert "name" in schema["properties"]
    assert "dataSource" in schema["properties"]
    assert "steps" in schema["properties"]


def test_get_datatype_schemas() -> None:
    """Test get_datatype_schemas with and without rollup support."""
    schemas_no_rollup = get_datatype_schemas(
        "test-type", "testType", Steps, "test description", supports_rollup=False
    )
    assert "test-type.list" in schemas_no_rollup
    assert "test-type.get" in schemas_no_rollup
    assert "test-type.create" in schemas_no_rollup
    assert "test-type.patch" in schemas_no_rollup
    assert "test-type.delete" in schemas_no_rollup
    assert "test-type.rollup" not in schemas_no_rollup

    schemas_rollup = get_datatype_schemas(
        "test-type", "testType", Steps, "test description", supports_rollup=True
    )
    assert "test-type.rollup" in schemas_rollup


def test_get_command_schemas() -> None:
    """Test get_command_schemas returns complete registry of CLI command schemas."""
    schemas = get_command_schemas()
    assert isinstance(schemas, dict)
    assert "steps.list" in schemas
    assert "userinfo" in schemas
    assert "profile.get" in schemas
    assert "settings.get" in schemas
    assert "devices.list" in schemas
    assert "subscribers.list" in schemas
    assert "subscriptions.list" in schemas


def test_cli_schema_unknown_command_error(capsys) -> None:
    """Test CLI error handling when introspecting an unknown schema command name."""
    with patch.object(
        sys, "argv", ["google-health-cli", "schema", "nonexistent.command"]
    ):
        with pytest.raises(SystemExit) as exit_info:
            main()
        assert exit_info.value.code == 1

    captured = capsys.readouterr()
    assert "Unknown command for schema lookup: nonexistent.command" in captured.err
