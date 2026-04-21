"""Resolve N-BaIoT folder whether it lives under data/ or repo root."""
from __future__ import annotations

import os

_PACKAGE_ROOT = os.path.abspath(os.path.dirname(__file__))


def _count_csvs(root: str) -> int:
    if not os.path.isdir(root):
        return 0
    n = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        n += sum(1 for f in filenames if f.endswith(".csv"))
    return n


def resolve_dataset_root() -> str:
    """
    Prefer a directory that actually contains .csv files.
    Typical layouts: <repo>/detection+of+... or <package>/data/detection+of+...
    """
    candidates = [
        os.path.normpath(os.path.join(os.path.dirname(_PACKAGE_ROOT), "detection+of+iot+botnet+attacks+n+baiot")),
        os.path.normpath(os.path.join(_PACKAGE_ROOT, "data", "detection+of+iot+botnet+attacks+n+baiot")),
    ]
    best: str | None = None
    best_n = -1
    for p in candidates:
        c = _count_csvs(p)
        if c > best_n:
            best_n = c
            best = p
    if best is not None and best_n > 0:
        return best
    raise FileNotFoundError(
        "N-BaIoT folder with CSV files not found. Checked:\n  " + "\n  ".join(candidates)
    )
