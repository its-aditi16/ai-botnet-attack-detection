# Azure Deployment Guide: IoT Botnet Attack Detection for Smart Campus Devices

This guide provides step-by-step instructions to deploy your Flask-based IoT Botnet Detection application as a Serverless API on Microsoft Azure, adhering exactly to the project requirements.

## Prerequisites
1. **Microsoft Azure Account**: Sign up for an [Azure Free Account](https://azure.microsoft.com/free/).
2. **Visual Studio Code (VS Code)**: Installed on your local machine.
3. **VS Code Extensions**:
   - Install the **Azure Tools** extension pack.
   - Install the **Python** extension.
4. **Azure Functions Core Tools**: Install this to develop and test functions locally.
5. **Azure CLI**: Install for command-line management of Azure resources.

---

## Step 1: Initialize the Azure Function Project
Your current project is a standard Flask app (`app.py`). To deploy this to Azure Functions, we need to create a Function App layout.

1. Open VS Code.
2. Click the **Azure** icon in the Activity Bar.
3. In the Workspace section, click the **Azure Functions** icon and select **Create Function...**.
4. Follow the prompts:
   - **Folder**: Select a new folder (e.g., `azure_function_app`).
   - **Language**: Select **Python v2**.
   - **Python interpreter**: Select your current virtual environment.
   - **Trigger**: Select **HTTP trigger**.
   - **Name**: Name it `PredictAPI`.
   - **Authorization level**: Select **Function** (this requires an API key for restricted access).

---

## Step 2: Refactor Code for Azure Functions
You will need to adapt the prediction code from your Flask `app.py` into the newly created `function_app.py` in your Azure Function folder.

1. In the new `function_app.py`, it will look something like this:
   ```python
   import azure.functions as func
   import pandas as pd
   import joblib
   import os
   import io
   from email.mime.text import MIMEText
   # ... [include your existing email configuration imports] ...
   
   app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

   @app.route(route="predict")
   def predict(req: func.HttpRequest) -> func.HttpResponse:
       # Read the file from req.files or req.get_body()
       file = req.files.get("file")
       data = pd.read_csv(file)
       
       # ... [run your prediction logic using joblib] ...
       
       # Return JSON response for malicious/benign with confidence
       return func.HttpResponse(
           '{"status": "SAFE", "confidence": 0.99}', 
           mimetype="application/json",
           status_code=200
       )
   ```
2. Copy the `model` scaler (`scaler.pkl`) and ML model (`botnet_model.pkl`) into this folder. Alternatively, keep them in Blob Storage (see next step).
3. Copy your `requirements.txt` from the main project and ensure it has:
   ```text
   azure-functions
   pandas
   scikit-learn
   joblib
   ```
   
---

## Step 3: Setup Azure Blob Storage (For Model)
Requirement: *Upload the model file to Azure Blob Storage and load it at cold start.*

1. Go to the [Azure Portal](https://portal.azure.com).
2. Search for **Storage Accounts** and click **Create**.
3. Create a unique Storage Account and navigate to **Containers** under the Data storage menu.
4. Add a container named `models`.
5. Upload your `botnet_model.pkl` and `scaler.pkl` to this container.
6. Note the **Access Key / Connection String** of the storage account (under Security + networking -> Access keys).

---

## Step 4: Setup Cosmos DB (for Alert Logging)
Requirement: *Log predictions + timestamps to Cosmos DB (or Table Storage) and tag high-risk events.*

1. In Azure Portal, search for **Azure Cosmos DB**.
2. Click **Create** > select **Azure Cosmos DB for NoSQL**.
3. Choose the **Free Tier discount**.
4. Create a Database named `BotnetDetection` and a Container named `Logs`.
5. Note your **URI** and **Primary Key**.

*Note: You can use `azure-cosmos` Python package in your Function to write JSON documents into this container.*

---

## Step 5: Configure Application Settings (Secrets)
Requirement: *Add security boundary demo: store secrets in Function App settings.*

1. In VS Code, go to the Azure extension > Workspace > Local Project.
2. Under your Function App, open `local.settings.json`.
3. Add your environment variables:
   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "AzureWebJobsStorage": "UseDevelopmentStorage=true",
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "AUTHORIZER_EMAIL": "your-authorizer-email@gmail.com",
       "SMTP_SERVER": "smtp.gmail.com",
       "SMTP_PORT": "587",
       "SMTP_USER": "your-email@gmail.com",
       "SMTP_PASSWORD": "your-app-password",
       "BLOB_CONNECTION_STRING": "<Your-Blob-Connection-String>",
       "COSMOS_DB_ENDPOINT": "<Your-Cosmos-URI>",
       "COSMOS_DB_KEY": "<Your-Cosmos-Key>"
     }
   }
   ```
4. Update your Python code to pull these keys via `os.environ.get("BLOB_CONNECTION_STRING")`.

---

## Step 6: Deploy to Azure
1. In VS Code, open the Azure tab.
2. Under **Resources** > **Function App**, click the **+ Create New...** icon > **Create Function App in Azure**.
3. Follow the Prompts:
   - Provide a unique name globally (e.g., `iot-botnet-api-aditi`).
   - Runtime stack: **Python 3.10** (or your version).
   - Location: Choose the region closest to you.
4. Once the infrastructure is created in Azure, right-click the new Function App in the VS Code extension and click **Deploy to Function App...**.
5. Confirm by clicking **Deploy**.
6. When deployment completes, Azure will prompt you to Upload Settings. Choose **Yes** to copy your local `local.settings.json` secrets up to Azure.

---

## Step 7: Secure the Endpoint with API Key
Because you set `AuthLevel.FUNCTION`, Azure automatically generated a default API key.
1. In the Azure Portal, go to your deployed Function App.
2. Click on **App keys** in the left menu.
3. Copy the `default` key.
4. In your Python simulator script, you must now send this key in the header `x-functions-key`.

---

## Step 8: Client Simulator Script (Testing)
Requirement: *Create an “IoT Telemetry Simulator” script that reads dataset rows and posts them to the scoring API.*

Create a separate Python script (`simulator.py`) on your local machine to send test telemetry to your Azure endpoint:

```python
import requests
import pandas as pd
import time

API_URL = "https://<your-function-app-name>.azurewebsites.net/api/predict"
API_KEY = "<your-copied-default-key>" # Security boundary via API Key

# Load subset of the dataset (e.g., Danmini Doorbell benign vs attack)
df = pd.read_csv("test_data.csv")

headers = {
    # Send the Function Key for Authentication
    "x-functions-key": API_KEY 
}

# Simulate sending row-by-row or batch telemetry
for index, row in df.head(10).iterrows():
    # Convert single row to CSV string format matching your app input
    csv_data = row.to_frame().T.to_csv(index=False)
    files = {"file": ("telemetry.csv", csv_data, "text/csv")}
    
    print(f"Sending telemetry {index} to Azure...")
    response = requests.post(API_URL, files=files, headers=headers)
    
    print(f"Response: {response.status_code}")
    print(response.json())
    time.sleep(1) # Simulate delay
```

You are now fully deployed on Azure fulfilling all project requirements!
