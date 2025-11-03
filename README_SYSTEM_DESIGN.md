## High-Level Architecture

```
+-------------------+                   HTTP         +--------------------+
|    Gradio UI      |  <---------------------------> |     FastAPI API    |
| (quick-n-dirty)   |                                 |  (routers/services)|
+-------------------+                                 +----------+---------+
                                                              | (cache-aside)
                                                  +-----------v-----------+
                                                  |        Redis          |
                                                  |  (sessions/cache,     |
                                                  |   task meta, WS feed) |
                                                  +-----------+-----------+
                                                              |
                                         +--------------------+---------------------+
                                         |                                          |
                                  +------v------+                             +-----v------+
                                  |   Celery    |   broker=Redis              |  MongoDB   |
                                  |  Workers    |---------------------------->| (cold store|
                                  |(ingestion & |      results/status         |  eval, docs|
                                  |  batch ops) |                             |  etc.)     |
                                  +------+------+                             +-----+------+
                                         |                                           ^
            parse -> chunk -> embed ->   |                                           |
                                         v                                           |
                                   +-----+------------------+                         |
                                   |   Preprocess Pipeline  |                         |
                                   | (Docling→Proposition→  |                         |
                                   |  LateChunk→Embed)      |                         |
                                   +-----------+------------+                         |
                                               |                                      |
                                               v                                      |
                                      +--------+--------+                             |
                                      |     Qdrant      |<----------------------------+
                                      | (hybrid: BM25 + |
                                      |  dense vectors) |
                                      +--------+--------+
                                               ^
                                               |
                                  +------------+------------+
                                  |  Retriever (Hybrid)     |
                                  |  + Reranker (LLM/RR)    |
                                  |  + Query Enhancer (LLM) |
                                  |  + Agent (CrewAI)       |
                                  +------------+------------+
                                               |
                                               v
                                        +------+------+
                                        |  Answer w/  |
                                        |  inline     |
                                        |  citations  |
                                        +-------------+
```

---

## Ingestion & Indexing Flow

```
[User/Dev] --POST /ingestion/start_job--> [FastAPI]
                                               |
                                               v   enqueue(job_id, files)
                                        [Redis (broker)]
                                               |
                                               v
                                        [Celery Worker(s)]
                                               |
                            ┌──────────────────┼──────────────────┐
                            v                  v                  v
                      [Docling]        [Propositioner]   [Late Chunking]
                      (parse PDF →     (rewrite into      (sentence-embed,
                       text/images)     clear props)       detect boundaries)
                            |                  |                  |
                            +------------------+------------------+
                                               v
                                          [Embedder]
                                         (e.g., E5)
                                               |
                                               v
                                upsert(chunks, vectors, metadata)
                                               |
                                               v
                                            [Qdrant]
                                               |
                                               v
                                       status→[MongoDB]
                                       progress→[Redis]
```

---

## Query → Retrieval → Rerank → Answer

```
(1) Gradio UI
     |
     |  /chat  (session_id, user_msg)
     v
+----+----------------------------------+
|             FastAPI                   |
|  - load session: get(session_id)      |
|      └─cache miss → load from MongoDB |
|         → hydrate into Redis          |
+----+--------------------+-------------+
     |                    |
     |                [Query Enhancer]
     |                (LLM rewrites query,
     |                 adds synonyms, fixes typos)
     v
[Retriever: Hybrid Search]
  - dense (Qdrant ANN)
  - sparse (BM25)
  - filters / metadata
     |
     v      top-k candidates
[Reranker]
  - LLM rerank or RR model
     |
     v      ordered passages
[Agent (CrewAI)]
  - multi-step reasoning
  - tool-use (retriever toggles)
     |
     v
[Answer Builder]
  - synthesize
  - inline citations (doc/page)
     |
     v
[FastAPI → UI]
  - stream tokens
  - persist chat in Redis (TTL)
  - async cold-store to MongoDB on TTL expiry
```

### Cache-Aside Session Pattern

```
+---------+        get(session_id)        +--------+     miss     +---------+
|  App    | -----------------------------> | Redis  | -----------> | MongoDB |
| (API)   | <----------------------------- |        | <----------- |         |
+---------+         set(session, TTL)      +--------+   hydrate    +---------+
```

---

## Evaluation Pipeline (Hit@K / MRR)

```
[FastAPI /evaluation/start]
           |
           v   enqueue(evaluation_id, Q/A set)
     [Redis (broker)]
           |
           v
     [Celery Worker]
           |
           v
   for each (q, relevant_doc):
        enhanced_q = LLM_enhance(q)
        cands = retriever(enhanced_q, k)
        ranked = reranker(cands)
        hit@k += any(doc_id==relevant_doc)
        mrr   += 1/rank(relevant_doc)
           |
           v
   persist metrics, per-combo variants
           |
           v
        [MongoDB]
           |
           v
 [FastAPI /evaluation/{id}] → UI
```

---

## Deployment Topology (docker-compose)

```
+-----------------+     +------------------+     +------------------+
|   gradio_app    |     |     fastapi      |     |    celery_worker |
|  (frontend)     | --> |  (app service)   | --> | (ingestion/eval) |
|                 |     |                  | <-- | (reads same code)|
+-----------------+     +---------+--------+     +------------------+
                                   |
                                   | broker/results
                                   v
                              +----+----+
                              |  Redis  |
                              +----+----+
                                   |
                                   |
                +------------------+------------------+
                |                                     |
           +----v----+                           +----v----+
           | Qdrant  |                           | MongoDB |
           | (vector |                           | (cold   |
           |  store) |                           |  store) |
           +---------+                           +---------+

(Optionally for demos)
+---------------+       +-----------------+
| Redis-Express |       |  Mongo-Express  |
+---------------+       +-----------------+
```

---
