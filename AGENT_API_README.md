# Recommendation Agent API Service

This document describes the standalone API service for the Recommendation Agent.

This service exposes the Agent's decision-making logic as a callable API endpoint, allowing it to be integrated into larger systems without needing to run the full recommendation pipeline.

## 1. How to Start the Service

To run this standalone service, execute the `app.py` file from within the `api/` directory.

```bash
# Navigate to the project root directory
cd d:\RecommendAgentProject

# Run the API service
python api/app.py
```

The service will start on `http://127.0.0.1:5001`.

## 2. API Endpoints

### Health Check

- **Endpoint**: `GET /health`
- **Description**: A simple endpoint to verify that the service is running.
- **Success Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "timestamp": "2026-05-02T12:00:00.000000Z"
  }
  ```

### Get Recommendation Strategy

- **Endpoint**: `POST /api/agent/recommend`
- **Description**: The main endpoint that takes a user query and returns the Agent's strategic decision.
- **Content-Type**: `application/json`

## 3. Testing with cURL

Here are three test cases you can use to interact with the running service via `curl`.

### Test Case 1: Standard Recommendation Request

This simulates a request from a user with existing history.

**Request:**
```bash
curl -X POST http://127.0.0.1:5001/api/agent/recommend \
-H "Content-Type: application/json" \
-d '{
  "user_id": 1,
  "query": "推荐一部类似《流浪地球》的科幻大片",
  "context": {
    "device": "web",
    "history": [123, 456]
  }
}'
```

**Expected Response:**
```json
{
  "intent": "recommend",
  "keywords": ["《流浪地球》的科幻大片"],
  "genres": ["科幻"],
  "mood": null,
  "strategy": {
    "use_ncf": true,
    "use_textcnn": true,
    "use_rules": true,
    "use_rag": false
  },
  "explain_required": true
}
```

### Test Case 2: Cold-Start User Request

This simulates a request from a new user with no history.

**Request:**
```bash
curl -X POST http://127.0.0.1:5001/api/agent/recommend \
-H "Content-Type: application/json" \
-d '{
  "user_id": 999,
  "query": "有没有好笑的喜剧片？",
  "context": {
    "device": "mobile",
    "history": []
  }
}'
```

**Expected Response:** (Note that `use_ncf` is `false`)
```json
{
  "intent": "recommend",
  "keywords": [],
  "genres": ["喜剧"],
  "mood": null,
  "strategy": {
    "use_ncf": false,
    "use_textcnn": true,
    "use_rules": true,
    "use_rag": false
  },
  "explain_required": true
}
```

### Test Case 3: Invalid Request (Missing Query)

This tests the input validation.

**Request:**
```bash
curl -X POST http://127.0.0.1:5001/api/agent/recommend \
-H "Content-Type: application/json" \
-d '{
  "user_id": 1,
  "context": {}
}'
```

**Expected Response (400 Bad Request):**
```json
{
  "error": "Missing or empty required field: query."
}
```
