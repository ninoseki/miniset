from typing import Literal

ParamStyleType = Literal["qmark", "format", "numeric", "named", "pyformat", "asyncpg"]
"""Parameter style."""

IdentifierQuoteCharacterType = Literal["`", '"']
"""Identifier for the quote character."""
