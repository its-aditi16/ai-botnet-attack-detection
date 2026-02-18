import os
import pandas as pd
import joblib

# -------- LOAD MODEL & SCALER --------
model = joblib.load("model/botnet_model.pkl")
scaler = joblib.load("model/scaler.pkl")

# -------- LOAD SAMPLE FILE --------
sample_path = r"data/detection+of+iot+botnet+attacks+n+baiot/Danmini_Doorbell/mirai_attacks/udp.csv"

data = pd.read_csv(sample_path)

# Remove label if exists
if "label" in data.columns:
    data = data.drop("label", axis=1)

# Scale
data_scaled = scaler.transform(data)

# Predict
predictions = model.predict(data_scaled)

print("Total Samples:", len(predictions))
print("Predicted Benign:", sum(predictions == 0))
print("Predicted Attack:", sum(predictions == 1))
