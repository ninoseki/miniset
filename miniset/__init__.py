import importlib.metadata

from .jinja_context import JinjaTemplateProcessor  # noqa: F401
from .types import ParamStyleType  # noqa: F401

__version__ = importlib.metadata.version("mini-set")
