from flask import Flask, request, render_template
import pandas as pd
import joblib

app = Flask(__name__)

model = joblib.load("model/botnet_model.pkl")
scaler = joblib.load("model/scaler.pkl")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    file = request.files["file"]
    data = pd.read_csv(file)

    if "label" in data.columns:
        data = data.drop("label", axis=1)

    data_scaled = scaler.transform(data)
    predictions = model.predict(data_scaled)

    benign = int((predictions == 0).sum())
    attack = int((predictions == 1).sum())
    total = len(predictions)

    status = "SAFE"
    if attack > benign:
        status = "BOTNET ATTACK DETECTED"

    return render_template("result.html",
                           total=total,
                           benign=benign,
                           attack=attack,
                           status=status)

if __name__ == "__main__":
    app.run(debug=True)
