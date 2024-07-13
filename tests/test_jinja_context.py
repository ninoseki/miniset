from datetime import date
from textwrap import dedent
from typing import Any, Union

import pytest
from jinja2 import DictLoader, Environment

from miniset import JinjaTemplateProcessor, ParamStyleType

_DATA = {
    "etc": {
        "columns": "project, timesheet, hours",
        "lt": "<",
        "gt": ">",
    },
    "request": {
        "project": {"id": 123, "name": "Acme Project"},
        "project_id": 123,
        "days": ["mon", "tue", "wed", "thu", "fri"],
        "day": "mon",
        "start_date": date.today(),
    },
    "session": {"user_id": "sripathi"},
}

WHERE_IN_TEMPLATE = "select * from timesheet where day in {{request.days | where_in}}"

MACROS_TEMPLATE = dedent(
    """{% macro OPTIONAL_AND(condition, expression, value) -%}
    {%- if condition -%}AND {{expression | sql_safe}}{{value}} {%- endif-%}
{%- endmacro -%}
SELECT 'x' from dual
WHERE 1=1
{{ OPTIONAL_AND(request.project_id != -1,
    "project_id = ", request.project_id)}}
{{ OPTIONAL_AND(request.unknown_column,
    "some_column = ", request.unknown_column) -}}
AND fixed_column = {{session.user_id}}"""
)


@pytest.mark.parametrize(
    "template,expected_query,expected_params",
    [
        (
            "{% import 'utils.sql' as utils %}select * from dual {{ utils.print_where(100) }}",
            "select * from dual WHERE dummy_col = %s",
            [100],
        )
    ],
)
def test_import(
    template: str,
    expected_query: str,
    expected_params: Union[list[Any], dict[Any, Any]],
):
    loader = DictLoader(
        {
            "utils.sql": dedent(
                """{% macro print_where(value) -%}
        WHERE dummy_col = {{value}}
        {%- endmacro %}"""
            )
        }
    )
    env = Environment(loader=loader)
    p = JinjaTemplateProcessor(env=env)
    query, bind_params = p.prepare_query(template, **_DATA)
    assert query == expected_query
    assert bind_params == expected_params


@pytest.mark.parametrize(
    "template,expected_query,expected_params",
    [
        (
            "select * from dummy {% include 'where_clause.sql' %}",
            "select * from dummy where project_id = %s",
            [123],
        )
    ],
)
def test_include(
    template: str,
    expected_query: str,
    expected_params: Union[list[Any], dict[Any, Any]],
):
    loader = DictLoader(
        {"where_clause.sql": "where project_id = {{request.project_id}}"}
    )
    env = Environment(loader=loader)
    p = JinjaTemplateProcessor(env=env)
    query, bind_params = p.prepare_query(template, **_DATA)
    assert query == expected_query
    assert bind_params == expected_params


@pytest.mark.parametrize(
    "template,expected_query,expected_params",
    [
        (
            "select * from dummy where project_id = {{ request.project_id }}",
            "select * from dummy where project_id = %s",
            [123],
        )
    ],
)
def test_precompiled_template(
    template: str,
    expected_query: str,
    expected_params: Union[list[Any], dict[Any, Any]],
):
    p = JinjaTemplateProcessor()
    query, bind_params = p.prepare_query(p._env.from_string(template), **_DATA)
    assert query == expected_query
    assert bind_params == expected_params


@pytest.mark.parametrize(
    "template,table_name,expected_query",
    [
        (
            "select * from {{table_name | identifier}}",
            "users",
            "select * from `users`",
        ),
        (
            "select * from {{table_name | identifier}}",
            ("myschema", "users"),
            "select * from `myschema`.`users`",
        ),
        ("select * from {{table_name | identifier}}", "a`b", "select * from `a``b`"),
    ],
)
def test_identifier_filter(
    template: str,
    table_name: Any,
    expected_query: str,
):
    p = JinjaTemplateProcessor(identifier_quote_character="`")
    query, _ = p.prepare_query(template, table_name=table_name)
    assert query == expected_query


@pytest.mark.parametrize(
    "template,param_style,expected_query,expected_params",
    [
        # asyncpg
        (
            "SELECT project, timesheet, hours FROM timesheet WHERE project_id = {{request.project_id}} and user_id = {{ session.user_id }}",
            "asyncpg",
            "SELECT project, timesheet, hours FROM timesheet WHERE project_id = $1 and user_id = $2",
            [123, "sripathi"],
        ),
        (
            "SELECT * FROM users WHERE user_name like {{ '%' ~ session.user_id ~ '%' }}",
            "format",
            "SELECT * FROM users WHERE user_name like %s",
            ["%sripathi%"],
        ),
        # bind params
        (
            "SELECT project, timesheet, hours FROM timesheet WHERE project_id = {{request.project_id}} and user_id = {{ session.user_id }}",
            "format",
            "SELECT project, timesheet, hours FROM timesheet WHERE project_id = %s and user_id = %s",
            [123, "sripathi"],
        ),
        # sql_safe filter
        (
            "SELECT {{etc.columns | sql_safe}} FROM timesheet",
            "format",
            "SELECT project, timesheet, hours FROM timesheet",
            [],
        ),
        (
            "select 'x' from dual where X {{etc.lt | sql_safe}} 1",
            "format",
            "select 'x' from dual where X < 1",
            [],
        ),
        # where_in filter
        (
            WHERE_IN_TEMPLATE,
            "format",
            "select * from timesheet where day in (%s,%s,%s,%s,%s)",
            ["mon", "tue", "wed", "thu", "fri"],
        ),
        (
            WHERE_IN_TEMPLATE,
            "qmark",
            "select * from timesheet where day in (?,?,?,?,?)",
            ["mon", "tue", "wed", "thu", "fri"],
        ),
        (
            WHERE_IN_TEMPLATE,
            "numeric",
            "select * from timesheet where day in (:1,:2,:3,:4,:5)",
            ["mon", "tue", "wed", "thu", "fri"],
        ),
        (
            WHERE_IN_TEMPLATE,
            "named",
            "select * from timesheet where day in (:where_in_1,:where_in_2,:where_in_3,:where_in_4,:where_in_5)",
            {
                "where_in_1": "mon",
                "where_in_2": "tue",
                "where_in_3": "wed",
                "where_in_4": "thu",
                "where_in_5": "fri",
            },
        ),
        (
            WHERE_IN_TEMPLATE,
            "pyformat",
            "select * from timesheet where day in (%(where_in_1)s,%(where_in_2)s,%(where_in_3)s,%(where_in_4)s,%(where_in_5)s)",
            {
                "where_in_1": "mon",
                "where_in_2": "tue",
                "where_in_3": "wed",
                "where_in_4": "thu",
                "where_in_5": "fri",
            },
        ),
        # macros
        (
            MACROS_TEMPLATE,
            "format",
            dedent(
                """SELECT 'x' from dual
WHERE 1=1
AND project_id = %s
AND fixed_column = %s"""
            ),
            [123, "sripathi"],
        ),
        (
            MACROS_TEMPLATE,
            "qmark",
            dedent(
                """SELECT 'x' from dual
WHERE 1=1
AND project_id = ?
AND fixed_column = ?"""
            ),
            [123, "sripathi"],
        ),
        (
            MACROS_TEMPLATE,
            "numeric",
            dedent(
                """SELECT 'x' from dual
WHERE 1=1
AND project_id = :1
AND fixed_column = :2"""
            ),
            [123, "sripathi"],
        ),
        # macro output
        (
            "{% macro week(value) -%} some_sql_function({{value}}) {%- endmacro %}SELECT 'x' from dual WHERE created_date > {{ week(request.start_date) }}",
            "format",
            "SELECT 'x' from dual WHERE created_date > some_sql_function(%s)",
            [date.today()],
        ),
        # set block
        (
            "{% set columns -%} project, timesheet, hours {%- endset %}select {{ columns | sql_safe }} from dual",
            "format",
            "select project, timesheet, hours from dual",
            [],
        ),
        # dict params
        (
            "INSERT INTO projects (info) VALUES({{request.project}})",
            "format",
            "INSERT INTO projects (info) VALUES(%s)",
            [{"id": 123, "name": "Acme Project"}],
        ),
    ],
)
def test_prepare_query(
    template: str,
    param_style: ParamStyleType,
    expected_query: str,
    expected_params: Union[list[Any], dict[Any, Any]],
):
    p = JinjaTemplateProcessor(param_style=param_style)
    query, params = p.prepare_query(template, **_DATA)
    assert query == expected_query
    assert params == expected_params
