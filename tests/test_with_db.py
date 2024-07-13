from typing import Optional

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel

from miniset import JinjaTemplateProcessor


class Hero(SQLModel, table=True):  # type: ignore
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


@pytest.fixture
def engine() -> Engine:
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def session(engine: Engine):
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture
def heros(session: Session) -> None:
    heros = [Hero(id=1, name="foo"), Hero(id=2, name="bar")]
    for hero in heros:
        session.add(hero)

    session.commit()


@pytest.mark.usefixtures("heros")
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


@pytest.mark.usefixtures("heros")
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
