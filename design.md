# Explainable Incident Commander AI - System Design

## 1. System Overview

The Incident Commander AI operates as an autonomous agent that ingests operational data, identifies anomalies, and provides explainable root cause analysis. It combines traditional observability with advanced ML and agentic reasoning.

## 2. Architecture Diagram (Text Flowchart)

Logs / Metrics / Traces
↓
[Telemetry Ingestion Layer] (FastAPI / Kafka)
↓
[Anomaly Detection] (Statistical Models)
↓
[Service Dependency Graph] (NetworkX)
↓
[Root Cause ML Model] (XGBoost / RandomForest)
↓
[SHAP Explainability Engine] (Explainable AI)
↓
[Agentic Reasoning Layer] (LangGraph / CrewAI + LLM)
↓
[Incident Summary + Explanation] (FastAPI / WebSocket)
↓
[Engineer Dashboard] (React / D3.js)

## 3. Component Details

### 3.1 Telemetry Ingestion Layer

- **Purpose**: Collects raw data from infrastructure.
- **Inputs**: Logs (ELK/Splunk), Metrics (Prometheus), Traces (Jaeger/OpenTelemetry).
- **Technology**: Kafka for stream processing, Elasticsearch for log storage.

### 3.2 Anomaly Detection & Service Graph

- **Anomaly Detection**: Uses statistical methods (Z-score, IQR) or ML to flag unusual metrics (CPU, Memory, Latency).
- **Dependency Graph**: Built using NetworkX. Represents service-to-service calls (e.g., Service A → Service B).
- **Function**: Determines the "blast radius" of an incident.

### 3.3 Root Cause Analysis (RCA) Engine

- **ML Model**: Trained on historical incident data.
- **Algorithm**: XGBoost or Random Forest for classification.
- **Input Features**:
  - CPU Usage
  - Memory Usage
  - Error Rate
  - Latency
  - Recent Deployment Flag
  - Downstream Failure Count
- **Output**: Probability score for each service being the root cause.

### 3.4 Explainability Engine (SHAP)

- **Purpose**: "Open the black box" of the ML model.
- **method**: SHAP (SHapley Additive exPlanations).
- **Output**: Feature importance values (e.g., "Latency contributed 45% to the prediction").

### 3.5 Agentic Reasoning Layer

- **Framework**: LangGraph or CrewAI.
- **LLM**: GPT-4 or Gemini via API.
- **Workflow**:
  1.  **Signal Collection**: Queries telemetry.
  2.  **Graph Analysis**: Traverses the dependency graph.
  3.  **Hypothesis Generation**: Formulates potential causes.
  4.  **Verification**: Checks hypotheses against SHAP values.
  5.  **Conclusion**: Synthesizes findings into a human-readable report.

## 4. Technology Stack

- **Frontend**: React, D3.js (for graph visualization).
- **Backend API**: FastAPI (Python).
- **Agent Framework**: LangGraph / CrewAI.
- **ML/AI**: Scikit-learn (XGBoost/RF), SHAP, NetworkX.
- **Database**: PostgreSQL (for incident history), Redis (for caching graph state).
- **Environment**: Docker containers.

## 5. Data Flow (Example Scenario)

1.  **Metric Spike**: `OrderService` latency jumps to 2000ms.
2.  **Detection**: Anomaly detector flags this event.
3.  **Graph Traversal**: Agent identifies `PaymentService` is a dependency of `OrderService`.
4.  **Hypothesis**: "Is PaymentService causing the latency?"
5.  **ML Check**: Model predicts `PaymentService` failure probability: 0.89.
6.  **Explanation**: SHAP analysis shows `PaymentService` CPU usage is the top feature.
7.  **Report**: "High confidence (89%) that PaymentService is root cause due to CPU saturation impacting latency."
