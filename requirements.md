# Explainable Incident Commander AI - Requirements

## 1. Overview

Explainable Incident Commander AI is an agentic SRE assistant designed to autonomously investigate production incidents, identify the most probable root cause across microservices, and explain its reasoning transparently using explainable AI (SHAP/LIME). The system does **not** auto-fix issues but provides high-confidence, evidence-backed explanations to reduce MTTR and engineer burnout.

## 2. Problem Statement

Modern microservice architectures (like those at FAANG/Amazon) suffer from:

- Noisy and overwhelming alerts.
- Scattered logs, metrics, and traces.
- Unclear service dependencies.
- High barrier to entry for junior engineers.
- Manual, time-consuming hypothesis testing by senior SREs.
- Existing tools answer "what" is happening, but not "why".

## 3. Core Capabilities

### 3.1 Autonomous Investigation

- **Data Ingestion**: Ingests logs, metrics (CPU, memory, latency, error rate), and traces.
- **Anomaly Detection**: Detects patterns indicative of failures.
- **Dependency Ingestion**: Builds and maintains a service dependency graph.

### 3.2 Root Cause Analysis (RCA)

- **Hypothesis Generation**: Formulates multiple potential reasons for a failure (e.g., "Service A latency due to database lock", "Service B error due to bad deployment").
- **Hypothesis Testing**: Correlates failures across services and verifies temporal ordering.
- **Ranking**: Ranks hypotheses by probability.

### 3.3 Explainability (The "Star Feature")

- **Transparent Reasoning**: Uses SHAP/LIME to explain _why_ a specific service is flagged as the root cause.
- **Feature Contribution**: Shows the contribution of specific metrics (e.g., "PaymentService latency: +47% contribution to failure prediction").
- **Human-Readable Explanations**: Converts ML output into clear text (e.g., "PaymentService is the root cause due to a sudden latency spike...").

### 3.4 Operational Constraints

- **Safety First**: The system explicitly **DOES NOT** perform auto-remediation (auto-fix).
- **Agentic Workflow**: Uses an agentic loop (Signal -> Graph -> Hypothesis -> Decision) rather than simple linear scripts.

## 4. User Scenarios

1.  **Incident Detection**: The system detects an anomaly in `OrderService`.
2.  **Investigation**: It traces the dependency to `PaymentService` and identifies a latency spike.
3.  **Explanation**: It reports to the dashboard: "Primary Root Cause: PaymentService (95% confidence). Evidence: Sudden 500ms latency increase correlated with OrderService timeouts. SHAP score for latency: +0.45."
4.  **Engineer Action**: The on-call engineer reviews the evidence and restarts the `PaymentService` pods, resolving the issue.

## 5. Non-Functional Requirements

- **Trustworthiness**: Explanations must be accurate and derived from actual data.
- **Performance**: Analysis should be near real-time to be useful during an active incident.
- **Scalability**: Must handle high-volume telemetry data from hundreds of microservices.
- **Interoperability**: Must integrate with standard observability formats (logs, metrics, traces).

## 6. Target Audience

- **Primary**: Site Reliability Engineers (SREs).
- **Secondary**: DevOps Engineers, Backend Developers.
