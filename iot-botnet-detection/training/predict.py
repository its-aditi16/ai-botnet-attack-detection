import os
import sys

import pandas as pd
import joblib
import numpy as np

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from label_utils import normalize_ground_truth_labels, select_numeric_features
from nbaiot_paths import resolve_dataset_root

# -------- LOAD MODEL & SCALER --------
model = joblib.load(os.path.join(_ROOT, "model", "botnet_model.pkl"))
scaler = joblib.load(os.path.join(_ROOT, "model", "scaler.pkl"))

# -------- LOAD SAMPLE FILE (prefers benign sample to show attack-like evaluation) --------
_root_ds = resolve_dataset_root()
for rel in (
    "Danmini_Doorbell/benign_traffic.csv",
    "Danmini_Doorbell/mirai_attacks/udp.csv",
):
    candidate = os.path.join(_root_ds, *rel.split("/"))
    if os.path.isfile(candidate):
        sample_path = candidate
        break
else:
    raise FileNotFoundError("No sample CSV found under " + _root_ds)

data = pd.read_csv(sample_path)
print("[*] Sample file:", sample_path)

has_gt = False
if "label" in data.columns:
    gt = normalize_ground_truth_labels(data["label"])
    if gt is not None and gt.notna().all():
        has_gt = True
        y_true = gt.astype(int).values
    X_raw = data.drop(columns=["label"])
else:
    X_raw = data

X = select_numeric_features(X_raw)
if hasattr(scaler, "feature_names_in_"):
    for col in scaler.feature_names_in_:
        if col not in X.columns:
            X[col] = 0.0
    X = X[list(scaler.feature_names_in_)]

data_scaled = scaler.transform(X)
predictions = model.predict(data_scaled)
proba = model.predict_proba(data_scaled)[:, 1]

print("Total Samples:", len(predictions))
print("Predicted Benign:", int((predictions == 0).sum()))
print("Predicted Attack:", int((predictions == 1).sum()))
print("High-confidence benign (P attack <= 0.25):", int((proba <= 0.25).sum()))
print("High-confidence attack (P attack >= 0.75):", int((proba >= 0.75).sum()))
print("Mean P(attack) %:", round(float(np.mean(proba) * 100), 2))
if has_gt:
    from sklearn.metrics import accuracy_score

    print("File row accuracy vs label column:", round(100 * accuracy_score(y_true, predictions), 2), "%")
