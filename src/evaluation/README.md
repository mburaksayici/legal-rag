# Evaluation System

The evaluation system tests retrieval performance by generating questions from PDFs and measuring how well the retrieval system finds the correct source documents.

## Overview

The evaluation workflow consists of three main steps:

1. **Question Generation**: An LLM agent (GPT-4o-mini) reads PDFs and generates targeted questions
2. **Retrieval**: Each question is used to query the retrieval system with configurable parameters
3. **Metrics Calculation**: Results are analyzed to compute hit rate, MRR, and other metrics

## API Endpoints

### Start Evaluation

```bash
POST /evaluation/start
```

**Request Body:**
```json
{
  "folder_path": "assets/sample_pdfs",
  "top_k": 10,
  "use_query_enhancer": false,
  "use_reranking": false,
  "num_questions_per_doc": 1
}
```

**Response:**
```json
{
  "evaluation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Evaluation started for folder: assets/sample_pdfs"
}
```

### Get Evaluation Status

```bash
GET /evaluation/{evaluation_id}
```

**Response:**
```json
{
  "evaluation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "folder_path": "assets/sample_pdfs",
  "retrieve_params": {
    "top_k": 10,
    "use_query_enhancer": false,
    "use_reranking": false
  },
  "num_documents_processed": 10,
  "created_at": "2025-11-02T10:00:00Z",
  "completed_at": "2025-11-02T10:05:00Z",
  "results_summary": {
    "hit_rate": 0.85,
    "mrr": 0.75,
    "hit_rate@1": 0.60,
    "hit_rate@3": 0.80,
    "hit_rate@5": 0.85,
    "hit_rate@10": 0.85,
    "total_questions": 10,
    "total_hits": 8
  }
}
```

### List All Evaluations

```bash
GET /evaluations?limit=50
```

**Response:**
```json
{
  "evaluations": [...],
  "total": 5
}
```

## Example Usage

```python
import requests

# Start evaluation
response = requests.post("http://localhost:8000/evaluation/start", json={
    "folder_path": "assets/sample_pdfs",
    "top_k": 10,
    "use_query_enhancer": False,
    "use_reranking": False,
    "num_questions_per_doc": 1
})

evaluation_id = response.json()["evaluation_id"]
print(f"Started evaluation: {evaluation_id}")

# Check status (wait a moment for it to complete)
import time
time.sleep(10)  # Wait for processing

status_response = requests.get(f"http://localhost:8000/evaluation/{evaluation_id}")
status = status_response.json()

if status["status"] == "completed":
    print("Results:", status["results_summary"])
```

## Metrics

### Hit Rate
Percentage of queries where the ground truth document was retrieved in the top-k results.

**Formula:** `hits / total_questions`

### Hit Rate @ K
Percentage of queries where the ground truth document was in the top K positions.

### Mean Reciprocal Rank (MRR)
Average of reciprocal ranks of the ground truth document.

**Formula:** `(1/rank_1 + 1/rank_2 + ... + 1/rank_n) / n`

Higher MRR means ground truth documents appear earlier in results.

## MongoDB Collections

### `evaluations`
Stores evaluation metadata and configuration:
- evaluation_id, folder_path, retrieve_params
- status, created_at, completed_at
- results_summary

### `evaluation_qa_pairs`
Stores individual Q&A pairs and retrieval results:
- evaluation_id, question, ground_truth_text
- source_document_path, retrieved_documents
- hit, rank

## Architecture

### Components

1. **SimplePDFPreprocess** (`src/data_preprocess_pipelines/simple_pdf_preprocess.py`)
   - Extracts text from PDF files using PyPDF2
   - Follows DataPreprocessBase pattern

2. **QuestionGeneratorAgent** (`question_generator_agent.py`)
   - Uses CrewAI with GPT-4o-mini
   - Structured output with Pydantic models
   - Generates fact-question pairs

3. **Evaluator** (`evaluator.py`)
   - Orchestrates the evaluation workflow
   - Uses RetrievalAgent for document retrieval
   - Stores results in MongoDB

4. **Metrics** (`metrics.py`)
   - Calculates hit rate, MRR, and other metrics
   - Extensible for additional metrics

5. **Service** (`service.py`)
   - Business logic layer
   - Manages evaluation lifecycle

## Adding New Metrics

To add a new metric:

1. Add function to `metrics.py`:
```python
def calculate_my_metric(qa_documents: List[QuestionAnswerDocument]) -> float:
    # Implementation
    return score
```

2. Update `calculate_all_metrics()` to include it:
```python
metrics["my_metric"] = calculate_my_metric(qa_documents)
```

## Notes

- Question generation uses first 3000 characters of each PDF to avoid token limits
- Evaluations run synchronously (can be moved to Celery for production)
- All data stored in MongoDB for persistence and analysis

