# IoT Botnet Attack Detection for Smart Campus Devices (Azure)

## Project Overview

This project implements a cloud security pipeline designed to detect IoT botnet behavior (such as Mirai/BASHLITE traffic patterns) in smart campus devices like CCTV cameras, smart plugs, and sensors.

Using the N-BaIoT dataset, we train a machine learning model to classify network traffic as benign or malicious. This model is deployed as a serverless scoring API on Azure Functions. The system simulates incoming IoT telemetry, scores it in real-time, logs high-risk events to a database, and triggers alerts for potential attacks.

## Table of Contents

- [Dataset](#dataset)
- [Technical Architecture](#technical-architecture)
- [Implementation Steps](#implementation-steps)
- [Deployment](#deployment)
- [Expected Results](#expected-results)
- [Evaluation Criteria](#evaluation-criteria)

## Dataset

**Source:** [N-BaIoT Dataset (UCI Machine Learning Repository)](https://archive.ics.uci.edu/ml/datasets/detection_of_IoT_botnet_attacks_N_BaIoT)

The dataset contains real traffic traces from 9 IoT devices infected by Mirai and BASHLITE. For this project scope (UG scale), we focus on 1-2 specific devices to demonstrate the detection capabilities.

- **Objective:** Classify traffic patterns as Benign vs. Malicious.
- **Features:** Statistical features extracted from network traffic (packet size, jitter, etc.).

## Technical Architecture

### Core Components
1.  **Azure Functions (Consumption Plan):** Hosts the serverless Python API for real-time scoring.
2.  **Azure Blob Storage:** Stores the trained machine learning model (`.pkl` file).
3.  **Azure Cosmos DB (Free Tier) / Table Storage:** distinct repository for logging prediction results and high-risk alerts.
4.  **Local/Client Script:** Python script to simulate IoT telemetry sending data to the cloud API.

### Tech Stack
-   **Language:** Python 3.x
-   **Frameworks:** FastAPI or Flask (for API), scikit-learn (for ML model).
-   **Tools:** VS Code, Azure Functions Extension.

## Implementation Steps

### 1. Data Preparation & Modeling
-   Download the N-BaIoT dataset.
-   Select data for 1-2 devices (combining benign and attack CSVs).
-   **Preprocessing:** Handle missing values, normalize features, and split into Training/Testing sets.
-   **Training:** Train a lightweight classifier (Logistic Regression or Random Forest) using `scikit-learn`.
-   **Export:** Save the trained model as a serialized file (`model.pkl`).

### 2. Cloud Backend (Azure)
-   **Model Storage:** Upload `model.pkl` to an Azure Blob Storage container.
-   **Serverless Function:**
    -   Create an Azure Function with an HTTP trigger.
    -   Implement logic to load the model (handling cold starts efficiently).
    -   Expose an endpoint (e.g., `/api/score`) that accepts JSON telemetry.
    -   Return prediction: `{"status": "benign/malicious", "confidence": 0.95}`.

### 3. Telemetry Simulation
-   Develop a Python script (`simulator.py`) that:
    -   Reads rows from the test dataset.
    -   Sends HTTP POST requests to the Azure Function endpoint.
    -   Simulates a stream of IoT device traffic.

### 4. Logging & Alerting
-   **Database:** Integrate the Azure Function with Cosmos DB to store every prediction with a timestamp.
-   **Alert Logic:**
    -   Check if `confidence > threshold` AND `prediction == "malicious"`.
    -   Trigger an email alert using SendGrid (Free Tier) or an SMTP server.

### 5. Security & Deployment
-   **Secrets Management:** Store API keys and connection strings in Azure Function App Settings (Environment Variables).
-   **Access Control:** Protect the Function endpoint with a Function Key.

## Deployment

1.  **VS Code:** Use the Azure Functions extension to deploy the function app directly to Azure.
2.  **Configuration:** ensuring `SCIKIT_LEARN_VERSION` matches between local training and Azure environment.
3.  **API Management (Optional):** Front the function with Azure API Management for rate limiting and additional security policies.

## Expected Results

-   A fully functional Cloud IDS (Intrusion Detection System) API.
-   Real-time detection of simulated botnet attacks.
-   Automated logging of security events to a cloud database.
-   Email alerts triggered by high-confidence malicious traffic detection.

## Evaluation Criteria

1.  **Model Performance:** Precision, Recall, and F1-Score on the test dataset.
2.  **API Reliability:** Stable response times and correct handling of concurrent requests.
3.  **System Integration:** precise end-to-end flow from Simulator -> API -> Database -> Alert.
4.  **Operational Best Practices:** meaningful logs, error handling, and secure configuration.
