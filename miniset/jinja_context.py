# Forked from https://github.com/apache/superset
# https://github.com/apache/superset/blob/master/LICENSE.txt
#
# Forked from https://github.com/sripathikrishnan/jinjasql
# The original version was created by Sripathi Krishnan and HashedIn Technologies Pvt. Ltd.
# https://github.com/sripathikrishnan/jinjasql/blob/master/LICENSE
from collections import OrderedDict
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

from jinja2 import DebugUndefined, Environment, Template
from jinja2.sandbox import SandboxedEnvironment
from markupsafe import Markup

from . import types
from .exceptions import MinisetTemplateException
from .extensions import SqlExtension
from .filters import build_identifier_filter, sql_safe

NONE_TYPE = type(None).__name__
ALLOWED_TYPES = (
    NONE_TYPE,
    "bool",
    "str",
    "unicode",
    "int",
    "long",
    "float",
    "list",
    "dict",
    "tuple",
    "set",
)


PARAM_STYLE_TO_PLACEHOLDER: Dict[str, Callable[[str, int], str]] = {
    "qmark": lambda _k, _i: "?",
    "format": lambda _k, _i: "%s",
    "numeric": lambda _k, i: f":{i}",
    "named": lambda k, _i: f":{k}",
    "pyformat": lambda k, _i: f"%({k})s",
    "asyncpg": lambda _k, i: f"${i}",
}


def dict_cast(bind_params: OrderedDict) -> Dict[Any, Any]:
    return dict(bind_params)


def list_cast(bind_params: OrderedDict) -> List[Any]:
    return list(bind_params.values())


PARAM_STYLE_TO_CAST: Dict[
    str, Callable[[OrderedDict], Union[Dict[Any, Any], List[Any]]]
] = {
    "qmark": list_cast,
    "format": list_cast,
    "numeric": list_cast,
    "named": dict_cast,
    "pyformat": dict_cast,
    "asyncpg": list_cast,
}


def validate_context_types(context: Dict[str, Any]) -> Dict[str, Any]:
    for key in context:
        arg_type = type(context[key]).__name__
        if arg_type not in ALLOWED_TYPES:
            raise MinisetTemplateException(
                f"Unsafe template value for key {key}: {arg_type}"
            )

    return context


class JinjaTemplateProcessor:
    def __init__(
        self,
        *,
        param_style: types.ParamStyleType = "format",
        identifier_quote_character: types.IdentifierQuoteCharacterType = '"',
        env: Optional[Environment] = None,
    ) -> None:
        self._context: Dict[str, Any] = {}

        self._env = env or SandboxedEnvironment(undefined=DebugUndefined)
        self._env.autoescape = True
        self._env.add_extension(SqlExtension)
        self._env.filters["bind"] = self._bind
        self._env.filters["where_in"] = self._where_in
        self._env.filters["sql_safe"] = sql_safe
        self._env.filters["identifier"] = build_identifier_filter(
            identifier_quote_character
        )

        self._param_style: types.ParamStyleType = param_style

        self._param_index: int = 0
        self._bind_params: OrderedDict[str, Any] = OrderedDict()

    def _bind_param(self, key: str, value: Any) -> str:
        self._param_index += 1
        new_key = f"{key}_{self._param_index}"
        self._bind_params[new_key] = value

        return PARAM_STYLE_TO_PLACEHOLDER[self._param_style](new_key, self._param_index)

    def _bind(self, value: Any, key: str) -> Union[Markup, str]:
        if isinstance(value, Markup):
            return value

        return self._bind_param(key, value)

    def _where_in(self, values: List[Any]) -> str:
        results = [self._bind_param("where_in", v) for v in values]
        clause = ",".join(results)
        return f"({clause})"

    def set_context(self, **kwargs: Any) -> None:
        """Set Jinja2 context"""
        self._context.update(kwargs)

    @contextmanager
    def _new_bind(self) -> Generator[None, None, None]:
        self._param_index = 0
        self._bind_params = OrderedDict()

        yield

    def prepare_query(
        self, query: Union[str, Template], **kwargs: Any
    ) -> Tuple[str, Union[List[Any], Dict[str, Any]]]:
        """Prepare a query template

        Args:
            query (Union[str, Template]): A query string/template

        Returns:
            query (str): A prepared query
            bind_params (Union[List[Any], Dict[str, Any]]): Bind params
        """
        template: Template = (
            query if isinstance(query, Template) else self._env.from_string(query)
        )
        return self._prepare_query(template, **kwargs)

    def _prepare_query(
        self, template: Template, **kwargs: Any
    ) -> Tuple[str, Union[List[Any], Dict[str, Any]]]:
        kwargs.update(self._context)
        context = validate_context_types(kwargs)

        cast = PARAM_STYLE_TO_CAST[self._param_style]
        with self._new_bind():
            query = template.render(context)
            return query, cast(self._bind_params)
