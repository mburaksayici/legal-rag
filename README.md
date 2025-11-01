# Financial RAG Project

[Financial RAG Project](https://github.com/mburaksayici/FinancialAdvisorGPT/)

---

### Project Template

I use different templates time to time to start with, for this one I'll start with **Netflix's Dispatch project structure.**
[https://github.com/zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)

Normally I generally use **FastAPI's official template:**
[https://github.com/tiangolo/full-stack-fastapi-template](https://github.com/tiangolo/full-stack-fastapi-template)

Or if I foresee the project requirements (eg. if I know I use redis+celery+flask I search for a specific combo), I research on templates to start with.

---

### Python Environment

Throughout history I've used plain pip, poetry, pdm.
For the project I'll use **uv**.

---

### Data Parsing & Ingestion System

The system now features a **Celery-based asynchronous ingestion pipeline** with real-time progress tracking via Redis.

#### New Celery-Based Ingestion Features

* **Dynamic Fan-Out Pattern**: Master task spawns individual subtasks for each document
* **Parallel Processing**: Documents processed simultaneously across multiple workers
* **Real-time Progress Tracking**: Monitor ingestion progress with detailed metrics per document
* **Redis-backed Status**: Progress data stored in Redis for fast access
* **Comprehensive Metrics**: Track successful/failed documents, estimated time remaining
* **Multiple File Types**: Support for PDF and JSON documents
* **Scalable Architecture**: Horizontal scaling with multiple Celery workers
* **Fault Tolerance**: Individual document failures don't stop the entire job

#### Progress Tracking Metrics

* Total documents to process
* Documents processed so far
* Successful vs failed document counts
* Current file being processed
* Estimated time remaining
* Progress percentage
* Real-time status updates

#### API Endpoints

All routes are organized in `src/posts/router.py` for clean architecture:

| Endpoint                       | Method | Description                           |
| ------------------------------ | ------ | ------------------------------------- |
| `/ingestion/start_job`         | POST   | Start folder ingestion job            |
| `/ingestion/start_single_file` | POST   | Start single file ingestion           |
| `/ingestion/status/{job_id}`   | GET    | Get job progress and status           |
| `/ingestion/jobs`              | GET    | List all active jobs                  |
| `/ingest`                      | POST   | Legacy endpoint (redirects to Celery) |
| `/chat`                        | POST   | Chat with AI assistant                |
| `/sessions/{session_id}`       | GET    | Get session information               |

#### Legacy Comparison

| Category                      | Description                                                 | Tools / Examples                          | Cost                              | Pros                              | Cons                                                           |
| ----------------------------- | ----------------------------------------------------------- | ----------------------------------------- | --------------------------------- | --------------------------------- | -------------------------------------------------------------- |
| **Data Parsing / Ingestion**  | Parsing with APIs or custom solutions depending on use-case | —                                         | —                                 | —                                 | —                                                              |
| **APIs**                      | High-quality baseline; no constraint on budget              | LangChain, MinerU                         | ~0.0001¢ per page (basic parsing) | High accuracy, easy setup         | Cost increases with scale                                      |
| **Custom Solutions**          | Necessary in some domains; customizable pipelines           | LangChain, PyMuPDF, Unstructured, Docling | Free (except man-hours)           | Custom logic, domain adaptability | Higher engineering effort                                      |
| **API Custom Development**    | Building your own parsing interface or logic                | LangChain Parse                           | —                                 | Flexible, extensible              | Maintenance overhead                                           |
| **Scalability Consideration** | Initially low cost, but can become expensive at scale       | —                                         | —                                 | Control over infrastructure       | "We can implement it ourselves" often becomes a harder problem |
| **Domain-Specific Parsing**   | Needed for specialized sectors                              | Defense Tech, Banking                     | —                                 | Tailored accuracy                 | Requires domain expertise                                      |

---

### Vector DB

Previously have used ChromaDB local, Pinecone Cloud.

**I have changed DB choice 3 times because:**

1. First attempted Milvus, because I love his CTO, he moved to VoyageAI later on and then company acquired by MongoDB. However I've read it has limited capability on free-oss tier.
2. Switched to ChromaDB for local tests, was about to keep it until I hit to celery task deadlocks reading from local disk which is obvious.
3. Want to test hybrid/fusion scoring that combines BM25 + dense search, Qdrant offers that, so I set up a standalone Qdrant container.

**Scaling:** Use APIs when you don’t want to deal with scaling. For small projects, a self-hosted setup can be sufficient.
**Industry Standards:** The decision also depends on the data protection standards required in the specific industry.
**Chosen Stack:** Currently using **Milvus**, since it supports both **local** and **cloud** environments.
**Side Note:** I'm waiting for **MongoDB** to release full **Vector DB** functionality for on-premise use. At the moment, it’s only available in their **Atlas Vector DB** (cloud version).

And going with local deployment of vector db.
First I'll keep vectordb local, then I'll move to another container.

---

### Embedding

Both Langchain CEO and Mivlus/VoyageAI CTO advises E5.
Performance concerns, I'll go with **E5-small**.

---

### Vector DB — Vector Index Decision

#### Zilliz / Milvus Strategy

Milvus (by Zilliz) recommends choosing a **vector index** based on data size and recall requirements.
The index type determines search speed, accuracy, and memory efficiency.

#### Heuristic to Use Index

| Data Size              | Recommended Index Type       | Description                                          |
| ---------------------- | ---------------------------- | ---------------------------------------------------- |
| 100% recall / accuracy | **Brute-force (FLAT)**       | Exact nearest neighbor search, slow but precise      |
| 10 MB – 2 GB           | **Inverted File (IVF)**      | Efficient for small-to-medium datasets               |
| 2 GB – 20 GB           | **Graph-based (HNSW)**       | Fast and memory-efficient for mid-scale datasets     |
| 20 GB – 200 GB         | **Hybrid (HNSW_SQ, IVF_PQ)** | Balances accuracy and compression                    |
| 200 GB+                | **Disk-based (DiskANN)**     | Optimized for large-scale vector data stored on disk |

I'll use the database default, **HNSW**, will work as good as FLAT on small data.

---

### Assumptions for Estimation

* 1 PDF = 10 pages
* 1 page = 500 words
* 15 words = 1 sentence
* 1 chunk = 3 sentences
* 1 PDF = 111 chunks

Thus,

* 1 chunk = 512 × 4 = 2 048 bytes ≈ 2 KB (unquantized float32)
* 1 PDF = 111 × 2 KB = 222 KB
* 100k PDF = 22 GB

Could be a rough estimate to choose indexing.

---

### Approximate Storage Estimation

| PDFs    | Pages per PDF | Words per Page | Total Words | Chunks (=Words/45) | Size per Vector | **Total Size** |
| ------- | ------------- | -------------- | ----------- | ------------------ | --------------- | -------------- |
| 1,000   | 10            | 500            | 5 M         | 111,111            | 4 KB            | ≈ **0.44 GB**  |
| 5,000   | 10            | 500            | 25 M        | 555,555            | 4 KB            | ≈ **2.2 GB**   |
| 50,000  | 10            | 500            | 250 M       | 5.56 M             | 4 KB            | ≈ **22 GB**    |
| 500,000 | 10            | 500            | 2.5 B       | 55.6 M             | 4 KB            | ≈ **222 GB**   |

---

### Tech Stack Options for the Requirements

Project requires:

* Conversation caching
* Document caching
* Vector DB
* Persistent DB for users/roles etc.

#### Milvus + Redis + MongoDB

* **Milvus** → Vector Database (stores embeddings and enables semantic search)
* **Redis** → Cache for chat history, conversation context, and asynchronous task results
* **MongoDB** → Persistent storage for sessions, documents, and chat logs
* **FastAPI** → Backend framework for API endpoints
* **Celery** → Task queue for background ingestion and embedding jobs

#### Milvus (or other) + Elasticsearch + MongoDB

* **Milvus (or other)** → Vector Database
* **Elasticsearch** → Keyword + hybrid search (BM25) and optional caching layer
* **MongoDB** → Persistent storage for metadata and history
* **FastAPI** → API layer
* **Celery / RQ / Dramatiq** → Asynchronous job management

#### Elasticsearch + MongoDB

* **Elasticsearch** → Both Vector + Keyword Search + Caching
* **MongoDB** → Persistent DB for sessions, chat, and documents
* **FastAPI** → Backend service
* **Celery / RQ / Dramatiq** → Async document ingestion and processing

#### PostgreSQL + pgvector (+ optional Redis)

* **PostgreSQL (pgvector)** → Combined structured DB + vector embeddings storage
* **Redis (optional)** → Cache for chat states and async job results
* **FastAPI** → API service
* **Celery / RQ / Dramatiq / BackgroundTasks** → For background jobs

For the sake of simplicity + flexibility I'll go with **Milvus + Redis + MongoDB** but I've heard complaints about Redis on big scales.

---

### EURLEX PDF Preparation Script

This repo includes a helper script to download, extract, and convert the **EURLEX57K JSON dataset** into PDFs.

#### Run Instructions

```bash
python -m src.assets.prepare_eurlex
```

or

```bash
python src/assets/prepare_eurlex.py
```

**Options**

* `--skipo` → skip wget step explicitly
* or set environment variable `SKIPO=1`

---

### Chunking Strategy

Milvus and Langchain technical executives both advise **Late Chunking**.

---

### Chat Agent

Framework to experiment orchestration: **CrewAI**

I've written my own pipelines before (Celery-based) for interview-prep.
Prompt templating on MongoDB is also a good choice for experimenting.

---

### Retriever

**AutomergingRetriever** is used.

#### Query Enhancement

Before retrieval, **query enhancement** is applied.

---

### Tech Stack for Session Management

**Pattern:** Cache Aside

App ↔ Redis ↔ MongoDB

#### Redis Express

To test if conversation in Redis:

```
GET session:0ea95f3a-b0ab-4e2e-92d8-6e227fd7715f
TTL session:0ea95f3a-b0ab-4e2e-92d8-6e227fd7715f
```

#### Ingestion

1. FastAPI triggers Celery
2. Celery creates tasks per file
3. `/ingestion/status` tracks job state

---

### Hybrid + Vector Search

As explained in the Vector DB section, Qdrant offers hybrid search (BM25 + dense).

---

### Query Enhancer

Example use case in [Financial RAG Project](https://github.com/mburaksayici/FinancialAdvisorGPT/):

User query:

> “Why Snowflake stocks are down?”

Enhanced queries:

* “snowflake stock down reason”
* “snowflake breaking news”

Finds reason: [Snowflake CEO retired](https://www.investopedia.com/snowflake-stock-plunges-after-company-names-new-ceo-issues-disappointing-guidance-8601946)

---

### Reranking

Reranking is essential because embedding similarity ≠ answer relevance.

Small systems may use **BM25 + LLM reranking**.
Larger setups may use **reranker models** for better accuracy.

This project uses a **reranking agent** to feed retrieved docs into LLM.
Test endpoint: `/retrieve` (toggle reranking and query enhancer).
