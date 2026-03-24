# Multi-Agent RAG Pipeline API Documentation

## Overview

This API provides granular access to each agent in the Multi-Agent RAG pipeline, as well as a streaming endpoint for real-time pipeline execution visualization.

---

## Base URL

```
http://localhost:5174
```

---

## Agent Routes

### 1. Gatekeeper Agent (Detection Agent)

**Endpoint:** `POST /api/agent/gatekeeper`

**Description:** Detects hallucinations and bias in AI responses using ML classifiers.

**Input:**
```json
{
  "user_message": "Who invented the light bulb?",
  "ai_response": "Thomas Edison invented the light bulb in 1879."
}
```

**Output:**
```json
{
  "agent": "gatekeeper",
  "hallucination_detected": true,
  "hallucination_type": "fabricated",
  "hallucination_confidence": 0.87,
  "bias_detected": false,
  "bias_type": "none",
  "bias_confidence": 0.12
}
```

**Performance Metrics:**
- Precision, Recall, F1-score (offline)
- Confusion Matrix
- Early-exit rate

---

### 2. SmartRouter Agent (Routing Agent)

**Endpoint:** `POST /api/agent/router`

**Description:** Routes detection results to the appropriate RAG agent category.

**Input:**
```json
{
  "hallucination": true,
  "hallucination_type": "fabricated",
  "hallucination_confidence": 0.87,
  "bias": false,
  "bias_type": "none",
  "bias_confidence": 0.12
}
```

**Output:**
```json
{
  "agent": "smartrouter",
  "category": "factual",
  "routing_logic": "Routed to 'factual' based on detection type"
}
```

**Performance Metrics:**
- Rule accuracy
- Misroute rate

---

### 3. Vector Knowledge Base Agent (Memory Agent)

**Endpoint:** `POST /api/agent/vectorkb/<category>`

**Categories:** `factual`, `logical`, `temporal`, `bias`

**Description:** Retrieves similar cases from the vector knowledge base using FAISS.

**Input:**
```json
{
  "query": "Who invented the light bulb? Thomas Edison invented the light bulb in 1879.",
  "k": 5
}
```

**Output:**
```json
{
  "agent": "vectorkb",
  "category": "factual",
  "total_docs": 150,
  "retrieved_count": 5,
  "top_matches": [
    {
      "user_message": "Who created the first practical light bulb?",
      "ai_response": "Thomas Edison developed the first commercially practical incandescent light bulb.",
      "similarity_score": 0.92
    }
  ]
}
```

**Performance Metrics:**
- Retrieval relevance
- Top-k hit rate
- FAISS search latency

---

### 4. RAG Agent (Correction Agent)

**Endpoint:** `POST /api/agent/rag/<category>`

**Categories:** `factual`, `logical`, `temporal`, `bias`

**Description:** Generates corrected responses based on retrieved context.

**Input:**
```json
{
  "user_message": "Who invented the light bulb?",
  "ai_response": "Thomas Edison invented the light bulb in 1879.",
  "k": 5
}
```

**Output:**
```json
{
  "agent": "rag",
  "category": "factual",
  "corrected_response": "Thomas Edison developed the first commercially practical incandescent light bulb...",
  "explanation": "5 matches, top: 0.92",
  "retrieved_count": 5
}
```

**Performance Metrics:**
- Correction reuse success
- Fallback frequency
- Downstream validation acceptance rate

---

### 5. OpenAI Validator Agent (External Judge #1)

**Endpoint:** `POST /api/agent/validator/openai`

**Description:** Validates factual accuracy using GPT-3.5.

**Input:**
```json
{
  "original": "Thomas Edison invented the light bulb in 1879.",
  "corrected": "Thomas Edison developed the first commercially practical incandescent light bulb...",
  "context": "5 matches, top: 0.92"
}
```

**Output:**
```json
{
  "agent": "openai_validator",
  "factual_score": 0.88,
  "explanation": "The correction provides more accurate historical context..."
}
```

**Performance Metrics:**
- Agreement with human labels
- API failure rate

---

### 6. Gemini Validator Agent (External Judge #2)

**Endpoint:** `POST /api/agent/validator/gemini`

**Description:** Validates coherence using Gemini Pro.

**Input:**
```json
{
  "original": "Thomas Edison invented the light bulb in 1879.",
  "corrected": "Thomas Edison developed the first commercially practical incandescent light bulb...",
  "context": "5 matches, top: 0.92"
}
```

**Output:**
```json
{
  "agent": "gemini_validator",
  "coherence_score": 0.84,
  "explanation": "The corrected response maintains good coherence while adding accuracy..."
}
```

**Performance Metrics:**
- Cross-model agreement
- Consistency across prompts

---

### 7. Consensus Engine (Arbitration Agent)

**Endpoint:** `POST /api/agent/consensus`

**Description:** Combines validator scores to reach consensus.

**Input:**
```json
{
  "original": "Thomas Edison invented the light bulb in 1879.",
  "corrected": "Thomas Edison developed the first commercially practical incandescent light bulb...",
  "context": "5 matches, top: 0.92"
}
```

**Output:**
```json
{
  "agent": "consensus",
  "factual_score": 0.88,
  "coherence_score": 0.84,
  "consensus_score": 0.86,
  "status": "auto_verified",
  "explanations": {
    "openai": "The correction provides more accurate historical context...",
    "gemini": "The corrected response maintains good coherence..."
  }
}
```

**Performance Metrics:**
- Auto-verification accuracy
- False acceptance/rejection rate

---

## Streaming Pipeline Endpoint

### Real-Time Pipeline Execution

**Endpoint:** `POST /api/pipeline/stream`

**Description:** Execute the full pipeline with real-time step-by-step updates via Server-Sent Events (SSE).

**Input:**
```json
{
  "user_message": "Who invented the light bulb?",
  "ai_response": "Thomas Edison invented the light bulb in 1879."
}
```

**Output:** Server-Sent Events stream

**Event Format:**
```
data: {"step": "gatekeeper", "status": "processing", "message": "Analyzing for hallucinations and bias..."}

data: {"step": "gatekeeper", "status": "complete", "data": {...}}

data: {"step": "router", "status": "processing", "message": "Routing to appropriate RAG agent..."}

data: {"step": "router", "status": "complete", "data": {...}}

... (continues for all agents)

data: {"step": "complete", "status": "success", "data": {...}}
```

**Steps in Order:**
1. `gatekeeper` - Detection
2. `router` - Routing
3. `vectorkb` - Knowledge retrieval
4. `rag` - Correction generation
5. `validator_openai` - OpenAI validation
6. `validator_gemini` - Gemini validation
7. `consensus` - Consensus calculation
8. `complete` - Final result

---

## Legacy Endpoint

### Standard Pipeline Execution

**Endpoint:** `POST /predict`

**Description:** Execute the full pipeline and return the final result (non-streaming).

**Input:**
```json
{
  "user_message": "Who invented the light bulb?",
  "ai_response": "Thomas Edison invented the light bulb in 1879."
}
```

**Output:**
```json
{
  "hallucination": true,
  "hallucination_type": "fabricated",
  "bias": false,
  "bias_type": "none",
  "explanation": "factual | H:0.87 | 5 matches, top: 0.92 | Cons:0.86",
  "corrected_response": "Thomas Edison developed the first commercially practical incandescent light bulb...",
  "confidence": 0.86,
  "status": "auto_verified"
}
```

---

## Health Check

**Endpoint:** `GET /health`

**Description:** Check API health status.

**Output:**
```json
{
  "status": "okay"
}
```

---

## Agent Performance Summary

| Agent | Input | Output | Performance Metrics |
|-------|-------|--------|---------------------|
| **Gatekeeper** | User message + AI response | Detection results | Precision, Recall, F1, Early-exit rate |
| **SmartRouter** | Detection result | Category | Rule accuracy, Misroute rate |
| **Vector KB** | Query + k | Retrieved documents | Retrieval relevance, Top-k hit rate, Latency |
| **RAG Agent** | User message + AI response + k | Corrected response | Correction reuse, Fallback frequency |
| **OpenAI Validator** | Original + Corrected + Context | Factual score | Agreement with human labels |
| **Gemini Validator** | Original + Corrected + Context | Coherence score | Cross-model agreement |
| **Consensus** | Validator scores | Final decision | Auto-verification accuracy, False acceptance/rejection |
| **Pipeline** | User message + AI response | System output | End-to-end latency, Throughput |

---

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK` - Success
- `400 Bad Request` - Missing or invalid parameters
- `500 Internal Server Error` - Server-side error
- `503 Service Unavailable` - Agent not initialized

**Error Response Format:**
```json
{
  "error": "Error description"
}
```

---

## Example Usage (JavaScript)

### Individual Agent Call
```javascript
const response = await fetch('http://localhost:5174/api/agent/gatekeeper', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_message: "Who invented the light bulb?",
    ai_response: "Thomas Edison invented the light bulb in 1879."
  })
});

const result = await response.json();
console.log(result);
```

### Streaming Pipeline
```javascript
const response = await fetch('http://localhost:5174/api/pipeline/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_message: "Who invented the light bulb?",
    ai_response: "Thomas Edison invented the light bulb in 1879."
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      console.log('Step:', data.step, 'Status:', data.status);
    }
  }
}
```

---

## Notes

- All agents operate independently and can be called individually for testing and debugging
- The streaming endpoint provides real-time visibility into the pipeline execution
- Each agent has clear input/output contracts and measurable performance metrics
- The system is audit-ready with full traceability of decisions at each step
