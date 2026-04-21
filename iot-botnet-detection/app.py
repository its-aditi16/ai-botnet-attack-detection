import os
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from flask import Flask, request, render_template
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import accuracy_score

from label_utils import normalize_ground_truth_labels, select_numeric_features
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableClient
import uuid
import datetime

app = Flask(__name__)

model = joblib.load("model/botnet_model.pkl")
scaler = joblib.load("model/scaler.pkl")

# --- Email Configuration ---
AUTHORIZER_EMAIL = os.environ.get("AUTHORIZER_EMAIL", "adithi.yt.1@gmail.com")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "adithi.yt.1@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "qplq asia rzah emxr")

# --- Azure Storage Configuration ---
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
BLOB_CONTAINER_NAME = "uploaded-telemetry"
TABLE_NAME = "PredictionLogs"

# Attack probability from RandomForest; used to split "looks benign" vs uncertain vs attack-like rows
CONFIDENCE_ATTACK = 0.75
CONFIDENCE_BENIGN = 0.25


def _align_features_to_scaler(X: pd.DataFrame, scaler) -> pd.DataFrame:
    if hasattr(scaler, "feature_names_in_"):
        expected = list(scaler.feature_names_in_)
        X = X.copy()
        for col in expected:
            if col not in X.columns:
                X[col] = 0.0
        return X[expected]
    return X


def send_alert_email(filename, attack_data_df):
    """Sends an email alert to the authorizer with attack details and data."""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = AUTHORIZER_EMAIL
        msg['Subject'] = f"🚨 URGENT: Botnet Attack Detected in {filename}"

        body = f"""
        Security Alert!
        
        A Botnet Attack has been detected during traffic analysis.
        
        File Analyzed: {filename}
        Total Attack Packets Detected: {len(attack_data_df)}
        """
        
        # Limit attachment size to prevent Google SMTP MaxSizeError (25MB limit)
        max_rows = 10000
        truncated = False
        if len(attack_data_df) > max_rows:
            attack_data_df = attack_data_df.head(max_rows)
            truncated = True
            body += f"\nNote: Due to email size limits, the attached CSV only contains the first {max_rows} attack packets.\n"
            
        body += """
        Please find the extracted attack data attached to this email for further forensic analysis.
        
        --
        IoT Botnet Detection System
        """
        msg.attach(MIMEText(body, 'plain'))

        # Attach CSV containing the attack data (truncated if necessary)
        csv_buffer = io.StringIO()
        attack_data_df.to_csv(csv_buffer, index=False)
        
        part = MIMEApplication(csv_buffer.getvalue().encode('utf-8'), Name=f"attack_data_{filename}")
        part['Content-Disposition'] = f'attachment; filename="attack_data_{filename}"'
        msg.attach(part)

        # Attempt to send email if credentials are changed from default
        if SMTP_PASSWORD != "your_app_password":
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"[*] Alert email sent successfully to {AUTHORIZER_EMAIL}")
        else:
            print(f"[*] Alert triggered for {filename}, but email NOT sent (Default credentials in use). Please set SMTP_USER and SMTP_PASSWORD.")

    except Exception as e:
        print(f"[!] Failed to send email alert: {e}")

@app.route("/")
def home():
    return render_template("landing.html")

@app.route("/analyze")
def analyze():
    return render_template("analyze.html")

@app.route("/predict", methods=["POST"])
def predict():
    file = request.files["file"]
    filename = file.filename if file.filename else "unknown_file.csv"
    file_bytes = file.read()
    
    # --- 1. Upload to Azure Blob Storage ---
    if AZURE_STORAGE_CONNECTION_STRING:
        try:
            blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)
            
            # Ensure container exists
            try:
                container_client.get_container_properties()
            except Exception:
                container_client.create_container()
            
            unique_blob_name = f"{uuid.uuid4()}-{filename}"
            blob_client = container_client.get_blob_client(unique_blob_name)
            blob_client.upload_blob(file_bytes, overwrite=True)
            print(f"[*] Uploaded {filename} to Azure Blob Storage ({unique_blob_name}).")
        except Exception as e:
            print(f"[!] Warning: Failed to upload to Blob Storage: {e}")

    # Read CSV (resetting stream since it was consumed)
    file_stream = io.BytesIO(file_bytes)
    data = pd.read_csv(file_stream)

    has_ground_truth = False
    y_true = None
    if "label" in data.columns:
        gt_series = normalize_ground_truth_labels(data["label"])
        if gt_series is not None and gt_series.notna().all():
            has_ground_truth = True
            y_true = gt_series.astype(int).values
        X_raw = data.drop(columns=["label"])
    else:
        X_raw = data

    X = select_numeric_features(X_raw)
    X = _align_features_to_scaler(X, scaler)

    data_scaled = scaler.transform(X)

    predictions = model.predict(data_scaled)
    proba_attack = model.predict_proba(data_scaled)[:, 1]

    total = len(predictions)
    attack = int(predictions.sum())
    benign = total - attack

    high_conf_attack = int((proba_attack >= CONFIDENCE_ATTACK).sum())
    high_conf_benign = int((proba_attack <= CONFIDENCE_BENIGN).sum())
    uncertain = total - high_conf_attack - high_conf_benign
    mean_attack_prob_pct = round(float(np.mean(proba_attack) * 100), 1) if total else 0.0

    rate = (attack / total) * 100 if total > 0 else 0

    filename_lower = (filename or "").lower()
    filename_hints_benign = "benign" in filename_lower

    gt_benign = gt_attack = None
    file_accuracy_pct = fp_count = fn_count = None
    all_rows_true_benign = False
    if has_ground_truth and y_true is not None:
        gt_benign = int((y_true == 0).sum())
        gt_attack = int((y_true == 1).sum())
        file_accuracy_pct = round(float(accuracy_score(y_true, predictions) * 100), 2)
        fp_count = int(((y_true == 0) & (predictions == 1)).sum())
        fn_count = int(((y_true == 1) & (predictions == 0)).sum())
        all_rows_true_benign = gt_attack == 0 and total > 0

    attack_like_rows = attack > 0
    evaluate_attack_in_benign_context = attack_like_rows and (
        filename_hints_benign or (has_ground_truth and all_rows_true_benign)
    )

    if attack > benign:
        status = "BOTNET ATTACK DETECTED"
    elif attack > 0:
        status = "ANOMALY_ATTACK_LIKE_ROWS"
    else:
        status = "SAFE"

    if attack > 0:
        attack_data = data.iloc[predictions == 1]
        if attack > benign:
            send_alert_email(filename, attack_data)
        elif evaluate_attack_in_benign_context and (
            high_conf_attack > 0 or attack >= max(3, int(0.02 * total))
        ):
            send_alert_email(filename, attack_data)

    # --- 2. Log Results to Azure Table Storage ---
    if AZURE_STORAGE_CONNECTION_STRING:
        try:
            table_client = TableClient.from_connection_string(conn_str=AZURE_STORAGE_CONNECTION_STRING, table_name=TABLE_NAME)
            # Ensure table exists safely
            try:
                table_client.create_table()
            except Exception:
                pass # Already exists
            
            entity = {
                "PartitionKey": "WebScan",
                "RowKey": str(uuid.uuid4()),
                "Timestamp": datetime.datetime.utcnow().isoformat(),
                "Filename": filename,
                "Status": status,
                "TotalPackets": total,
                "AttackPackets": attack,
                "AttackRate": float(round(rate, 1))
            }
            table_client.create_entity(entity=entity)
            print(f"[*] Logged prediction event to Azure Table Storage.")
        except Exception as e:
            print(f"[!] Warning: Failed to log to Table Storage: {e}")

    return render_template(
        "result.html",
        total=total,
        benign=benign,
        attack=attack,
        rate=round(rate, 1),
        status=status,
        high_conf_attack=high_conf_attack,
        high_conf_benign=high_conf_benign,
        uncertain=uncertain,
        mean_attack_prob_pct=mean_attack_prob_pct,
        has_ground_truth=has_ground_truth,
        gt_benign=gt_benign,
        gt_attack=gt_attack,
        file_accuracy_pct=file_accuracy_pct,
        fp_count=fp_count,
        fn_count=fn_count,
        filename_hints_benign=filename_hints_benign,
        evaluate_attack_in_benign_context=evaluate_attack_in_benign_context,
        attack_like_rows=attack_like_rows,
        all_rows_true_benign=all_rows_true_benign,
    )

if __name__ == "__main__":
    app.run(debug=True)
