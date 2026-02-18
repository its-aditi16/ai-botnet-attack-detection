import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

# -------- BASE PATH (absolute path) --------
base_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "../data/detection+of+iot+botnet+attacks+n+baiot"))

all_data = []

# -------- LOOP THROUGH ALL DEVICES --------
for device in os.listdir(base_path):
    device_path = os.path.join(base_path, device)

    if not os.path.isdir(device_path):
        continue

    for root, dirs, files in os.walk(device_path):
        for file in files:
            if file.endswith(".csv"):
                file_path = os.path.join(root, file)

                df = pd.read_csv(file_path)

                # Labeling
                if "benign" in file.lower():
                    df["label"] = 0
                else:
                    df["label"] = 1

                all_data.append(df)

# -------- COMBINE EVERYTHING --------
data = pd.concat(all_data, ignore_index=True)

# -------- CLEAN --------
data = data.dropna()

X = data.drop("label", axis=1)
y = data["label"]

# -------- SCALE --------
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# -------- SPLIT --------
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42
)

# -------- TRAIN --------
model = RandomForestClassifier(n_estimators=50, random_state=42)
model.fit(X_train, y_train)

# -------- EVALUATE --------
y_pred = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred))

# -------- SAVE --------
os.makedirs("model", exist_ok=True)
joblib.dump(model, "model/botnet_model.pkl")
joblib.dump(scaler, "model/scaler.pkl")

print("Model saved successfully")
