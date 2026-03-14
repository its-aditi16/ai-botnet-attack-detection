import pandas as pd
from app import send_alert_email
import os

print("Testing direct email dispatch...")

# Create a small dummy dataframe that looks like an attack
data = {
    'feature1': [0.1, 0.2, 0.3],
    'feature2': [1.1, 1.2, 1.3],
}
df = pd.DataFrame(data)

# Force the environment variables just in case
os.environ["AUTHORIZER_EMAIL"] = "adithi.yt.1@gmail.com"
os.environ["SMTP_USER"] = "adithi.yt.1@gmail.com"
os.environ["SMTP_PASSWORD"] = "qplq asia rzah emxr"

send_alert_email("test_attack_log.csv", df)
print("Test script finished.")
