from __future__ import annotations

import os
import sys
import zlib

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from label_utils import normalize_ground_truth_labels, select_numeric_features
from nbaiot_paths import resolve_dataset_root

SKIP_BASENAMES = frozenset({"demonstrate_structure.csv"})


def _cap_rows(X: pd.DataFrame, y: pd.Series, cap: int, file_path: str) -> tuple[pd.DataFrame, pd.Series]:
    """Keep training feasible on huge CSVs while preserving per-file diversity."""
    if len(X) <= cap:
        return X.reset_index(drop=True), y.reset_index(drop=True)
    seed = zlib.adler32(file_path.encode("utf-8", errors="ignore")) & 0x7FFFFFFF
    idx = X.sample(n=cap, random_state=seed).index
    return X.loc[idx].reset_index(drop=True), y.loc[idx].reset_index(drop=True)


def _filename_default_label(file_path: str) -> int:
    low = file_path.replace("\\", "/").lower()
    if "benign" in low:
        return 0
    return 1


def _load_file_labeled(file_path: str, row_cap: int) -> tuple[pd.DataFrame, pd.Series]:
    """Load at most row_cap rows from disk when N-BaIoT has no per-row label column."""
    default = _filename_default_label(file_path)
    header = pd.read_csv(file_path, nrows=0).columns
    has_label_col = "label" in header

    if has_label_col:
        df = pd.read_csv(file_path, low_memory=False)
    else:
        df = pd.read_csv(file_path, nrows=row_cap, low_memory=False)

    if has_label_col:
        y_raw = normalize_ground_truth_labels(df["label"])
        if y_raw is not None and y_raw.notna().any():
            mask = y_raw.notna()
            if mask.sum() > 0:
                X = select_numeric_features(df.loc[mask].drop(columns=["label"]))
                y = y_raw.loc[mask].astype(int)
                return _cap_rows(X, y, row_cap, file_path)

    df_features = df.drop(columns=["label"], errors="ignore") if "label" in df.columns else df
    X = select_numeric_features(df_features)
    y = pd.Series(default, index=df.index, dtype=int)
    return _cap_rows(X, y, row_cap, file_path)


def _align_feature_columns(parts: list[tuple[pd.DataFrame, pd.Series]]) -> tuple[pd.DataFrame, pd.Series]:
    if not parts:
        raise RuntimeError("No CSV samples loaded.")

    common: set[str] | None = None
    for X, _ in parts:
        cols = set(X.columns)
        common = cols if common is None else common & cols

    if not common:
        raise RuntimeError("No overlapping numeric feature columns across CSV files.")

    ordered = sorted(common)
    xs, ys = [], []
    for X, y in parts:
        xs.append(X.reindex(columns=ordered))
        ys.append(y)
    return pd.concat(xs, ignore_index=True), pd.concat(ys, ignore_index=True)


base_path = resolve_dataset_root()
print("[*] Dataset root:", base_path, flush=True)
ROWS_PER_FILE_CAP = int(os.environ.get("NBAIOT_ROWS_PER_FILE_CAP", "12000"))
print(f"[*] Rows per CSV cap: {ROWS_PER_FILE_CAP} (NBAIOT_ROWS_PER_FILE_CAP)", flush=True)

parts: list[tuple[pd.DataFrame, pd.Series]] = []

for device in sorted(os.listdir(base_path)):
    device_path = os.path.join(base_path, device)
    if not os.path.isdir(device_path):
        continue
    for root, _dirs, files in os.walk(device_path):
        for file in sorted(files):
            if not file.endswith(".csv"):
                continue
            if file in SKIP_BASENAMES:
                print(f"[*] Skip non-data file: {file}")
                continue
            file_path = os.path.join(root, file)
            try:
                pair = _load_file_labeled(file_path, ROWS_PER_FILE_CAP)
                if pair[0].shape[0] == 0:
                    print(f"[!] Skip empty after load: {file_path}")
                    continue
                parts.append(pair)
            except Exception as e:
                print(f"[!] Skip {file_path}: {e}", flush=True)

print(f"[*] Loaded {len(parts)} CSV files", flush=True)
X, y = _align_feature_columns(parts)

mask = X.notna().all(axis=1) & y.notna()
X = X.loc[mask].reset_index(drop=True)
y = y.loc[mask].reset_index(drop=True)

total_pool = len(y)
print("[*] Total rows (cleaned pool):", total_pool, flush=True)

# RandomForest does not scale to multi-million-row pools; train on a stratified cap.
MAX_TRAIN_ROWS = int(os.environ.get("NBAIOT_MAX_TRAIN_ROWS", "200000"))
if total_pool > MAX_TRAIN_ROWS and y.nunique() > 1:
    X, _, y, _ = train_test_split(
        X, y, train_size=MAX_TRAIN_ROWS, random_state=42, stratify=y
    )
    print(
        f"[*] Using stratified training sample: {len(y)} rows "
        f"(cap {MAX_TRAIN_ROWS}; set NBAIOT_MAX_TRAIN_ROWS to change)",
        flush=True,
    )

print("[*] Rows used for fit:", len(y), flush=True)
print("Class balance (training pool):", flush=True)
print(y.value_counts(), flush=True)
print(y.value_counts(normalize=True).round(4), flush=True)

scaler = StandardScaler()
print("[*] Fitting scaler + training RandomForest (this may take a few minutes)…", flush=True)
X_scaled = scaler.fit_transform(X)

stratify = y if y.nunique() > 1 else None
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=stratify
)

model = RandomForestClassifier(
    n_estimators=int(os.environ.get("NBAIOT_N_ESTIMATORS", "120")),
    random_state=42,
    class_weight="balanced_subsample",
    n_jobs=int(os.environ.get("NBAIOT_RF_JOBS", "-1")),
    min_samples_leaf=2,
    min_samples_split=4,
    max_depth=int(os.environ.get("NBAIOT_MAX_DEPTH", "32")),
    max_features="sqrt",
    max_samples=0.85,
    oob_score=True,
    bootstrap=True,
)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print("Holdout accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred, digits=4))
prec, rec, f1, _ = precision_recall_fscore_support(
    y_test, y_pred, average=None, labels=[0, 1], zero_division=0
)
print(
    "Per-class (0=benign, 1=attack) precision, recall, F1:",
    f"benign P/R/F1={prec[0]:.4f}/{rec[0]:.4f}/{f1[0]:.4f}",
    f"attack P/R/F1={prec[1]:.4f}/{rec[1]:.4f}/{f1[1]:.4f}",
)
print("Confusion matrix [[TN FP],[FN TP]] (true 0,1 × pred 0,1):")
print(confusion_matrix(y_test, y_pred))
if getattr(model, "oob_score_", None) is not None:
    print(f"OOB score: {model.oob_score_:.4f}")

out_dir = os.path.join(_ROOT, "model")
os.makedirs(out_dir, exist_ok=True)
joblib.dump(model, os.path.join(out_dir, "botnet_model.pkl"))
joblib.dump(scaler, os.path.join(out_dir, "scaler.pkl"))

print("[*] Model saved to", out_dir)
