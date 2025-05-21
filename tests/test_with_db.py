from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from miniset import JinjaTemplateProcessor


@pytest.mark.usefixtures("heroes")
def test_format(engine: Engine) -> None:
    p = JinjaTemplateProcessor(param_style="named")

    query, bind_params = p.prepare_query(
        "SELECT * FROM hero WHERE id = {{ id }}",
        id=1,
    )

    with engine.connect() as conn:
        res = conn.execute(text(query), bind_params)
        rows = list(res)
        assert len(rows) == 1


@pytest.mark.usefixtures("heroes")
def test_qmark(engine: Engine) -> None:
    p = JinjaTemplateProcessor(param_style="qmark")

    query, bind_params = p.prepare_query(
        "SELECT * FROM hero WHERE id = {{ id }}",
        id=1,
    )

    with engine.connect() as conn:
        res = conn.exec_driver_sql(query, tuple(bind_params))
        rows = list(res)
        assert len(rows) == 1


def test_where_in(engine: Engine, heroes: list[Any]) -> None:
    p = JinjaTemplateProcessor()

    query, bind_params = p.prepare_query(
        "SELECT * FROM hero WHERE id IN {{ ids | where_in(null_if_empty=True) }}",
        ids=[],
    )
    with engine.connect() as conn:
        res = conn.exec_driver_sql(query, tuple(bind_params))
        rows = list(res)
        assert len(rows) == 0
