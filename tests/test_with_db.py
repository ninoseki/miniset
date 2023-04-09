from typing import Optional

import pytest
from sqlalchemy import create_engine
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
def test_prepare_query(engine: Engine) -> None:
    p = JinjaTemplateProcessor(param_style="qmark")

    query, bind_params = p.prepare_query(
        "SELECT * FROM hero WHERE id = {{ id }}",
        id=1,
    )

    with engine.connect() as conn:
        res = conn.execute(query, *bind_params)
        rows = list(res)
        assert len(rows) == 1
