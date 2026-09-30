"""Entrypoint. Implementation lives in polymer_eval/bench/."""

from .bench.task import polymer_bench, polymer_hle, polymer_lab_bench
from .bench.constants import ANSWER_TYPES, DATASETS

__all__ = ["polymer_bench", "polymer_hle", "polymer_lab_bench", "DATASETS", "ANSWER_TYPES"]
