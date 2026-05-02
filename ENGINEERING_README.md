# Engineering & Explainability Layer README

This document details the engineering enhancements implemented in Phase 5, focusing on making the AI Recommendation System more robust, observable, configurable, and interpretable.

## 1. Core Engineering Modules

### 1.1 Configuration System (`config/settings.py`)

- **Purpose**: To centralize all tunable parameters and feature flags, removing hardcoded values from the application logic.
- **Key Contents**:
  - `DEBUG_MODE_ENABLED`: A global switch to enable or disable the output of detailed debug information.
  - `EXPLAIN_ENABLED`: A switch to turn on or off the generation of per-item explanations.
  - `LOG_FILE_PATH` & `LOG_LEVEL`: Configuration for the logging system.
  - `FUSION_WEIGHTS`: Dictionaries defining the contribution of each model (NCF, TextCNN, Rules) in different scenarios (default, cold-start, semantic query).
- **Usage**: Other modules (like `orchestrator` and `app.py`) import settings from this file to guide their behavior.

### 1.2 Logging System (`logging/logger.py`)

- **Purpose**: To provide a standardized, application-wide logging mechanism.
- **Features**:
  - **Dual Output**: Logs are simultaneously sent to the console (for real-time monitoring) and a file (`logs/app.log`).
  - **Log Rotation**: Log files are automatically rotated when they reach 10MB, keeping the 5 most recent logs to prevent disk space issues.
  - **Request Tracing**: Each API request is assigned a unique `request_id`, which is included in all related log entries, making it easy to trace a single request's journey through the system.
- **Usage**: The pre-configured `logger` instance is imported and used throughout `app.py` to record key events like incoming requests, Agent decisions, and final responses.

### 1.3 Explainability Layer (`explain/explanation_generator.py`)

- **Purpose**: To translate the machine-level decision process into human-readable text for each recommended item.
- **Mechanism**:
  1. The `score_engine` was refactored to track the `sources` (e.g., `["ncf", "textcnn"]`) that contributed to each movie's final score.
  2. `explanation_generator.py` takes the final recommendation list as input.
  3. For each item, it looks at its `sources` and maps them to predefined, user-friendly text templates (e.g., `ncf` -> "Considering movies you've liked...").
  4. The generated explanation string is then attached to the movie item in the final API response.

### 1.4 Debug & Observability Layer (`debug/debug_builder.py`)

- **Purpose**: To create a rich, structured `debug_trace` object that provides deep insight into the AI pipeline's execution for a given request.
- **Key Information Captured**:
  - `agent_decision`: The full output from the Recommendation Agent.
  - `models_used`: Which recommendation models were activated by the Orchestrator.
  - `fusion_weights`: The final, normalized weights used to combine the model results.
  - `raw_results_count`: The number of candidates returned by each model *before* fusion and filtering.
- **Control**: The inclusion of this entire `debug_trace` object in the final API response is controlled by the `DEBUG_MODE_ENABLED` flag in `config/settings.py`.

## 2. Integration into the Main Application (`app.py`)

The `/api/ai/recommend/full` endpoint in `app.py` was significantly enhanced to act as the central integration point for all these engineering modules:

1.  **On Request Start**: A `request_id` is generated and the incoming request is logged.
2.  **Agent & Orchestrator Call**: The core pipeline remains the same.
3.  **Build Debug Trace**: If `DEBUG_MODE_ENABLED` is true, the `debug_builder` is called to assemble the trace object.
4.  **Generate Explanations**: If `EXPLAIN_ENABLED` is true, the `explanation_generator` is called, and its output is attached to each recommendation item.
5.  **Final Response**: The final JSON payload is constructed, conditionally including the `debug_trace` and `explanation` fields based on the configuration.
6.  **On Request End**: The successful completion is logged.
7.  **Error Handling**: Any exception during the process is caught and logged in detail, including a full traceback.

By implementing this layer, the system is no longer a "black box." It provides clear, actionable insights for developers (via logs and debug traces) and transparent, trustworthy explanations for end-users.
