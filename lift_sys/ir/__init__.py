"""IR package exports."""

from .models import *  # noqa: F401,F403
from .parser import IRParser, ParserConfig

__all__ = ["IRParser", "ParserConfig"] + [name for name in globals() if name[0].isupper()]
