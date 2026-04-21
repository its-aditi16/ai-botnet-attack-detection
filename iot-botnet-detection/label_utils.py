"""Shared helpers for per-row labels and numeric feature columns."""
from __future__ import annotations

import numpy as np
import pandas as pd


def select_numeric_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a numeric-only feature frame.

    Some N-BaIoT CSVs can contain mixed-type columns (pandas reads them as object).
    In that case, we try to coerce to numeric instead of silently dropping them.
    """
    if df.empty:
        return df.copy()

    numeric = df.select_dtypes(include=[np.number]).copy()
    non_numeric_cols = [c for c in df.columns if c not in numeric.columns]
    if not non_numeric_cols:
        return numeric

    # Try converting object columns to numeric; keep only those with signal.
    coerced = {}
    for col in non_numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce")
        # Keep if we got at least 90% non-null values (tolerate a little noise).
        if s.notna().mean() >= 0.90:
            coerced[col] = s

    if coerced:
        coerced_df = pd.DataFrame(coerced, index=df.index)
        out = pd.concat([numeric, coerced_df], axis=1)
        return out

    return numeric


def normalize_ground_truth_labels(series: pd.Series) -> pd.Series | None:
    """
    Map a label column to 0 (benign) / 1 (attack). Unknown values become NaN.
    Returns None if nothing could be mapped.
    """
    out: list[float] = []
    for v in series:
        if pd.isna(v):
            out.append(np.nan)
            continue
        if isinstance(v, (bool, np.bool_)):
            out.append(int(v))
            continue
        if isinstance(v, (int, np.integer)):
            if int(v) in (0, 1):
                out.append(float(int(v)))
            else:
                out.append(np.nan)
            continue
        if isinstance(v, float):
            if np.isnan(v):
                out.append(np.nan)
            elif float(v) in (0.0, 1.0):
                out.append(float(int(v)))
            else:
                out.append(np.nan)
            continue
        if isinstance(v, str):
            t = v.strip().lower()
            if t in ("0", "benign", "normal", "safe", "b", "neg", "negative"):
                out.append(0.0)
            elif t in ("1", "attack", "malicious", "botnet", "a", "pos", "positive"):
                out.append(1.0)
            else:
                out.append(np.nan)
            continue
        out.append(np.nan)

    s = pd.Series(out, index=series.index, dtype=float)
    if s.notna().sum() == 0:
        return None
    return s
