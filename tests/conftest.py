from typing import Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel


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
def heroes(session: Session):
    heroes = [Hero(id=1, name="foo"), Hero(id=2, name="bar")]
    for hero in heroes:
        session.add(hero)

    session.commit()

    return heroes
