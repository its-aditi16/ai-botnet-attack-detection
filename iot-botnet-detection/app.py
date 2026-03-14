import os
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from flask import Flask, request, render_template
import pandas as pd
import joblib

app = Flask(__name__)

model = joblib.load("model/botnet_model.pkl")
scaler = joblib.load("model/scaler.pkl")

# --- Email Configuration ---
AUTHORIZER_EMAIL = os.environ.get("AUTHORIZER_EMAIL", "adithi.yt.1@gmail.com")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "adithi.yt.1@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "qplq asia rzah emxr")

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
    
    # Read CSV (optimized with engine='c' which is default, but ensuring memory efficiency)
    data = pd.read_csv(file)
    
    # Store columns for label drop without making full dataframe copies
    cols = data.columns
    if "label" in cols:
        X = data.drop("label", axis=1)
    else:
        X = data

    # Scale using numpy array directly
    data_scaled = scaler.transform(X)
    
    # Predict (returns numpy array)
    predictions = model.predict(data_scaled)

    # Ultra-fast numpy counting (orders of magnitude faster than pandas sums)
    total = len(predictions)
    attack = int(predictions.sum()) # Since attacks are 1, sum() is the count of attacks
    benign = total - attack

    rate = (attack / total) * 100 if total > 0 else 0
    
    status = "SAFE"
    if attack > benign:
        status = "BOTNET ATTACK DETECTED"
        
        # ONLY slice the dataframe if an attack is actually detected (saves massive time)
        # Using boolean indexing directly on the original data 
        attack_data = data.iloc[predictions == 1]
        
        # Trigger the email alert
        send_alert_email(filename, attack_data)

    return render_template("result.html",
                           total=total,
                           benign=benign,
                           attack=attack,
                           rate=round(rate, 1),
                           status=status)

if __name__ == "__main__":
    app.run(debug=True)
