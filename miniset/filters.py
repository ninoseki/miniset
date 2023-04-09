# Forked from https://github.com/apache/superset
# https://github.com/apache/superset/blob/master/LICENSE.txt
#
# Forked from https://github.com/sripathikrishnan/jinjasql
# The original version was created by Sripathi Krishnan and HashedIn Technologies Pvt. Ltd.
# https://github.com/sripathikrishnan/jinjasql/blob/master/LICENSE
from typing import Any, Iterable, List, Union

from markupsafe import Markup

from . import types


def dummy_sql_safe(value: Any) -> Any:
    """Dummy sql_safe filter for linting

    Args:
        value (Any): Value

    Returns:
        Any: Value
    """
    return value


def dummy_where_in(values: List[Any], mark: str = "'") -> str:
    """Dummy where_in filter for linting

    Args:
        values (List[Any]): Values
        mark (str, optional): Quote mark. Defaults to "'".

    Returns:
        str: A string representation of a parenthesis list suitable for an IN expression
    """

    def quote(value: Any) -> str:
        if isinstance(value, str):
            value = value.replace(mark, mark * 2)
            return f"{mark}{value}{mark}"
        return str(value)

    joined_values = ", ".join(quote(value) for value in values)
    return f"({joined_values})"


def sql_safe(value: Any) -> Markup:
    """Filter to mark the value of an expression as safe for inserting in a SQL statement

    Args:
        value (Any): Value

    Returns:
        Markup: Markup
    """
    return Markup(value)


def build_identifier_filter(
    identifier_quote_character: types.IdentifierQuoteCharacterType,
):
    """Build identifier filter based on a quote character

    Args:
        identifier_quote_character (types.IdentifierQuoteCharacterType): Quote character for identifier
    """

    def quote_and_escape(value: str):
        # Escape double quote with 2 double quotes,
        # or escape backtick with 2 backticks
        return (
            identifier_quote_character
            + value.replace(identifier_quote_character, identifier_quote_character * 2)
            + identifier_quote_character
        )

    def identifier_filter(raw_identifier: Union[Iterable[str], str]):
        if isinstance(raw_identifier, str):
            raw_identifier = (raw_identifier,)

        if not isinstance(raw_identifier, Iterable):
            raise ValueError("identifier filter expects a string or an Iterable")

        return Markup(".".join(quote_and_escape(s) for s in raw_identifier))

    return identifier_filter
