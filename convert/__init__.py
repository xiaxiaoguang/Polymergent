"""Dataset converters. Add a new source as convert/<name>.py and register it in pipeline.CONVERTERS."""

from .pipeline import main, run_convert

__all__ = ["main", "run_convert"]
