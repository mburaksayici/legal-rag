# RAG Boilerplate Gradio UI

Web interface for the RAG Boilerplate  Document RAG System.

## Features

### 4 Main Tabs

1. **💬 Chat** - Interactive chat with  documents
   - Session management and history
   - Source citation
   - Message persistence

2. **🔍 Retrieval Testing** - Test document retrieval
   - Configurable parameters (top-k, query enhancer, reranking)
   - View retrieved documents with scores
   - Compare different configurations

3. **📥 Ingestion** - Document ingestion management
   - Start batch ingestion jobs
   - Monitor job progress in real-time
   - View active jobs
   - Auto-refresh status updates

4. **📊 Evaluation** - Retrieval system evaluation
   - Start evaluation jobs
   - View metrics (Hit Rate, MRR)
   - Compare different configurations
   - Reuse questions across evaluations

## Running Locally

### Prerequisites
- Python 3.11+
- FastAPI backend running on port 8000

### Setup

```bash
cd gradio_app

# Using uv (recommended)
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

### Run

```bash
# Set API base URL (optional, defaults to localhost:8000)
export API_BASE_URL=http://localhost:8000

# Start the app
python app.py
```

The UI will be available at http://localhost:7860

## Running with Docker

The Gradio UI is included in the docker-compose setup:

```bash
# From project root
docker-compose up gradio-ui
```

Access at http://localhost:7860

## Configuration

The app uses the `API_BASE_URL` environment variable to connect to the backend:

- **Docker**: Automatically set to `http://app:8000`
- **Local**: Defaults to `http://localhost:8000`, can be overridden

## Architecture

```
gradio_app/
├── app.py           # Main Gradio application with 4 tabs
├── api_client.py    # API wrapper for backend calls
├── components.py    # UI formatters and helpers
├── requirements.txt # Python dependencies
├── Dockerfile       # Container definition
└── README.md        # This file
```

## API Endpoints Used

### Chat
- `POST /chat` - Send chat messages
- `GET /sessions` - List all sessions
- `GET /sessions/{session_id}` - Get session history

### Retrieval
- `POST /retrieve` - Test document retrieval

### Ingestion
- `POST /ingestion/start_job` - Start batch ingestion
- `GET /ingestion/status/{job_id}` - Check job status
- `GET /ingestion/jobs` - List active jobs

### Evaluation
- `POST /evaluation/start` - Start evaluation
- `GET /evaluation/{evaluation_id}` - Get evaluation results
- `GET /evaluations` - List all evaluations

### Assets
- `GET /assets/list` - Browse assets folder

