

### Project Template 

I use different templates time to time to start with, for this one I'll start with  Netflix's Dispatch project structure. 

https://github.com/zhanymkanov/fastapi-best-practices

Normally I generally use  FastAPI's official template : github.com/tiangolo/full-stack-fastapi-template

Or if I foresee the project requirements (eg. if I know I use redis+celery+flask I search for a specific combo), I research on templates to start with .

### Python Environment

Throughout history I've used plain pip, poetry, pdm. For the project I'll use uv.  

### Data Parsing 

| Category | Description | Tools / Examples | Cost | Pros | Cons |
|-----------|--------------|------------------|------|------|------|
| **Data Parsing / Ingestion** | Parsing with APIs or custom solutions depending on use-case | — | — | — | — |
| **APIs** | High-quality baseline; no constraint on budget | LangChain, MinerU | ~0.0001¢ per page (basic parsing) | High accuracy, easy setup | Cost increases with scale |
| **Custom Solutions** | Necessary in some domains; customizable pipelines | LangChain, PyMuPDF, Unstructured, Docling | Free (except man-hours) | Custom logic, domain adaptability | Higher engineering effort |
| **API Custom Development** | Building your own parsing interface or logic | LangChain Parse | — | Flexible, extensible | Maintenance overhead |
| **Scalability Consideration** | Initially low cost, but can become expensive at scale | — | — | Control over infrastructure | “We can implement it ourselves” often becomes a harder problem |
| **Domain-Specific Parsing** | Needed for specialized sectors | Defense Tech, Banking | — | Tailored accuracy | Requires domain expertise |


### Vector DB
Previously have used ChromaDB local, Pinecone Cloud. 

Going with Milvus, because I love his CTO, he moved to VoyageAI later on and then company acquired by MongoDB.


- **Scaling:** Use APIs when you don’t want to deal with scaling. For small projects, a self-hosted setup can be sufficient.  
- **Industry Standards:** The decision also depends on the data protection standards required in the specific industry.  
- **Chosen Stack:** Currently using **Milvus**, since it supports both **local** and **cloud** environments.  
- **Side Note:** I'm waiting for **MongoDB** to release full **Vector DB** functionality for on-premise use. At the moment, it’s only available in their **Atlas Vector DB** (cloud version).

And going with local deployment of vector db. First I'll keep vectordb local, then I'll move to another container. 

### Embedding 

Both Langchain CEO and Mivlus/VoyageAI CTO advises E5. 
Performance concerns, I'll go with E5-small. 


### 🧠 Vector DB — Vector Index Decision

#### Zilliz / Milvus Strategy

Milvus (by Zilliz) recommends choosing a **vector index** based on data size and recall requirements. The index type determines search speed, accuracy, and memory efficiency.

---

#### Heuristic to Use Index

| Data Size | Recommended Index Type | Description |
|------------|------------------------|--------------|
| 100% recall / accuracy | **Brute-force (FLAT)** | Exact nearest neighbor search, slow but precise |
| 10 MB – 2 GB | **Inverted File (IVF)** | Efficient for small-to-medium datasets |
| 2 GB – 20 GB | **Graph-based (HNSW)** | Fast and memory-efficient for mid-scale datasets |
| 20 GB – 200 GB | **Hybrid (HNSW_SQ, IVF_PQ)** | Balances accuracy and compression |
| 200 GB+ | **Disk-based (DiskANN)** | Optimized for large-scale vector data stored on disk |

---

#### Assumptions for Estimation

- **1 PDF = 10 pages**  
- **1 page = 500 words**  
- **15 words = 1 sentence**  
- **1 chunk = 3 sentences**

Thus,  
> 1 chunk = 45 words

---

## Approximate Storage Estimation

| PDFs | Pages per PDF | Words per Page | Total Words | Chunks (=Words/45) | Size per Vector | **Total Size** |
|------|----------------|----------------|--------------|--------------------|-----------------|----------------|
| 1,000 | 10 | 500 | 5 M | 111,111 | 4 KB | ≈ **0.44 GB** |
| 5,000 | 10 | 500 | 25 M | 555,555 | 4 KB | ≈ **2.2 GB** |
| 50,000 | 10 | 500 | 250 M | 5.56 M | 4 KB | ≈ **22 GB** |
| 500,000 | 10 | 500 | 2.5 B | 55.6 M | 4 KB | ≈ **222 GB** |

---

- For **≤ 2 GB**, a simple IVF index is efficient.  
- For **10–200 GB**, prefer HNSW or hybrid indexes for faster queries.  
- For **200 GB+**, DiskANN or Milvus Disk Index becomes necessary.  
- Use heuristics above to plan scaling for document-heavy RAG systems.

---


### Tech Stack Options for the requirements

Project requires : 

- Conversation caching
- Document caching
- Vector DB
- Persistent DB for users/roles etc.

There are options, some  may bloat your tech stack but may bloat it for a reason, some tech stack is simple enough with less headache. 

For such a project, those are the general options I've seen people are using successfully. 


#### Milvus + Redis + MongoDB

- **Milvus** → Vector Database (stores embeddings and enables semantic search)  
- **Redis** → Cache for chat history, conversation context, and asynchronous task results  
- **MongoDB** → Persistent storage for sessions, documents, and chat logs  
- **FastAPI** → Backend framework for API endpoints  
- **Celery** → Task queue for background ingestion and embedding jobs  


#### Milvus + Elasticsearch + MongoDB

- **Milvus** → Vector Database  
- **Elasticsearch** → Keyword + hybrid search (BM25) and optional caching layer for query results  
- **MongoDB** → Persistent storage for metadata and history  
- **FastAPI** → API layer  
- **Celery / RQ / Dramatiq** → Asynchronous job management  


#### Elasticsearch + MongoDB

- **Elasticsearch** → Both Vector + Keyword Search + Caching (short-TTL indices)  
- **MongoDB** → Persistent DB for sessions, chat, and documents  
- **FastAPI** → Backend service  
- **Celery / RQ / Dramatiq** → Async document ingestion and processing  


#### PostgreSQL + pgvector (+ optional Redis)

- **PostgreSQL (pgvector)** → Combined structured DB + vector embeddings storage  
- **Redis (optional)** → Cache for chat states and async job results  
- **FastAPI** → API service  
- **Celery / RQ / Dramatiq / BackgroundTasks** → For background jobs  


For the sake of simplicity+flexibility I'll go with Milvus + Redis + MongoDB but I've heard complaints about Redis on big scales.

Depending on the needs you can switch to other tech stack.

## EURLEX PDF Preparation Script

This repo includes a helper script to download, extract, and convert the EURLEX57K JSON dataset into PDFs.

Prerequisites:
- `wget` available on your system
- Install deps (optional, only when you want to generate PDFs):
  - `reportlab`
  - `python-dotenv` (already listed in `requirements/base.txt`)

Run:
- Module form:
```bash
python -m src.assets.prepare_eurlex
```
- Script form:
```bash
python src/assets/prepare_eurlex.py
```

Options:
- `--skipo` → skip wget step explicitly
- Or set environment variable `SKIPO=1` to skip wget

Behavior:
- Always processes all splits: train, test, dev (no split selection)

Artifacts:
- Zip: `assets/datasets.zip`
- Extracted: `assets/dataset/`
- PDFs output: `assets/pdfs/`




### Chunking Strategy 

Milvus and Langchain technical executives both advices Late Chunking.

I'll fill this part later on. TO DO .

Original Text : 

Having regard to Article 83 of the Treaty establishing the European Economic Community, which provides that an advisory committee consisting of experts designated by the Governments of Member States shall be attached to the Commission and consulted by the latter on transport matters whenever the Commission considers this desirable, without prejudice to the powers of the transport section of the Economic and Social Committee; Having regard to Article 153 of that Treaty, which provides that the Council shall, after receiving an opinion from the Commission, determine the rules governing the committees provided for in that\n\nTreaty;\n\nHaving received an Opinion from the Commission;\n\n## Main Body:\n\nthat the Rules of the Transport Committee shall be as follows:\n\nThe Committee shall consist of experts on transport matters designated by the Governments of Member States. Each Government shall designate one expert or two experts selected from among senior officials of the central administration. It may, in addition, designate not more than three experts of acknowledged competence in, respectively, the railway, road transport and inland waterway sectors.\n\nEach Government may designate an alternate for each member of the Committee appointed by it; this alternate shall satisfy conditions the same as those for the member of the Committee whom he replaces.\n\nAlternates shall attend Committee meetings and take part in the work of the Committee only in the event of full members being unable to do so.\n\nCommittee members and their alternates shall be appointed in their personal capacity and may not be bound by any mandatory instructions.\n\nThe term of office for members and their alternates shall be two years. Their appointments may be renewed.\n\nIn the event of the death, resignation or compulsory retirement of a member or alternate, that member or alternate shall replaced for the remainder of his term of office.\n\nThe Government which appointed a member or alternate may compulsorily retire that member or alternate only if the member or alternate no longer fulfils the conditions required for the performance of his duties.\n\nThe Committee shall, by an absolute majority of members present and voting, elect from among the members appointed by virtue of their status as senior officials of the central administration a Chairman and Vice-Chairman, who shall serve as such for two years. Should the Chairman or Vice-Chairman cease to hold office before the period for which he was elected has expired, a replacement for him shall be elected for the remainder of the period for which he was originally elected.\n\nNeither the Chairman nor the Vice-Chairman may be re-elected.\n\nThe Committee shall be convened by the Chairman, at the request of the Commission, whenever the latter wishes to consult it. The Commission's request shall state the purpose of the consultation.\n\nWhen the Committee is consulted by the Commission, it shall present the latter with a report setting out the conclusions reached as a result of its deliberations. It shall do likewise if the Commission entrusts it with the study of a specific problem. The Commission shall also be entitled to consult the Committee orally. The minutes of the Committee shall be sent to the Commission.\n\nThe Commission shall be invited to send its representatives to meetings of the Committee and its working parties.\n\nThe Committee shall, by an absolute majority of members present and voting, adopt rules of procedure laying down its methods of working.\n\nThe Committee may, whenever such action appears to it to be necessary for the purposes of formulating an opinion, seek the assistance of any suitably qualified person, obtain any advice and hold hearings. Such action may, however, be taken only with the consent of the Commission.\n\n0\n\nThe expenses of the Committee shall be included in the estimates of the Commission.\n\n## Attachments:\n\nDone at Brussels, 15 September 1958.\n\nFor the Council The President L. Erhard


##### Proposition Model
| **Original Legal Text** | **Propositionized Output** |
|--------------------------|-----------------------------|
| *Having regard to <mark>Article 83</mark> of the Treaty establishing the European Economic Community, which provides that an advisory committee consisting of experts designated by the Governments of Member States shall be attached to the Commission and consulted by the latter on transport matters whenever the Commission considers this desirable, without prejudice to the powers of the transport section of the Economic and Social Committee;* | **<mark>Article 83</mark> of the Treaty establishing the European Economic Community <mark>provides for</mark> an advisory committee consisting of experts designated by the Governments of Member States.**  <br> **The advisory committee shall be attached to the Commission and consulted on transport matters whenever the Commission considers it desirable.**  <br> **The advisory committee shall not prejudice the powers of the transport section of the Economic and Social Committee.** |
| *Having regard to <mark>Article 153</mark> of that Treaty, which provides that the Council shall, after receiving an opinion from the Commission, determine the rules governing the committees provided for in that Treaty;* | **<mark>Article 153</mark> of the Treaty <mark>provides for the Council to determine</mark> the rules governing the committees provided for in that Treaty after receiving an opinion from the Commission.** |
| *Having <mark>received</mark> an Opinion from the Commission;* | ⚠️ **The Council <mark>shall receive</mark> an Opinion from the Commission.** |
| *That the Rules of the Transport Committee <mark>shall be as follows</mark>:* | ⚠️ **The Rules of the Transport Committee <mark>shall consist of experts on transport matters designated by the Governments of Member States</mark>.** |
| *The Committee shall consist of experts on transport matters designated by the Governments of Member States.* | **<mark>Each Government shall designate one expert or two experts selected from among senior officials of the central administration.</mark>** |
| *It may, in addition, designate not more than three experts of acknowledged competence in, respectively, the railway, road transport and inland waterway sectors.* | **Each Government may designate not more than three experts of acknowledged competence in the <mark>railway, road transport, and inland waterway</mark> sectors.** |
| *Each Government may designate an alternate for each member of the Committee appointed by it; this alternate shall satisfy conditions the same as those for the member of the Committee whom he replaces.* | **Each Government may designate an alternate for each member of the Committee appointed by it.**  <br> **The alternate shall satisfy conditions the same as those for the member of the Committee whom he replaces.** |
| *Committee members and their alternates shall be appointed in their personal capacity and may not be bound by any mandatory instructions.* | **Committee members and their alternates shall be appointed in their personal capacity.** <br> **Committee members and their alternates may not be bound by any mandatory instructions.** |
| *The term of office for members and their alternates shall be two years. Their appointments may be renewed.* | **The term of office for members and their alternates shall be two years.** <br> **<mark>Appointments for members and their alternates may be renewed.</mark>** |
| *In the event of the death, resignation or compulsory retirement of a member or alternate, that member or alternate shall <mark>replaced</mark> for the remainder of his term of office.* | **In the event of the death, resignation, or compulsory retirement of a member or alternate, that member or alternate shall <mark>be replaced</mark> for the remainder of his term of office.** |



##### Meaning Comparison

| Clause | Original intention | Propositionized version | Meaning change |
|--------|--------------------|--------------------------|----------------|
| “Having regard to Article 83…” | Cites the legal authority and basis. | Declarative factual statement of Article 83’s content. | ✅ No change (stylistic only). |
| “Attached to the Commission…” | Defines advisory linkage to Commission. | Rephrased identically. | ✅ Same meaning. |
| “Without prejudice…” | Ensures existing powers remain. | Restated identically. | ✅ Same meaning. |
| “Having regard to Article 153…” | Cites second authority. | Declarative factual restatement. | ✅ Same meaning. |
| “Having received an Opinion…” | Indicates past procedural completion. | “Shall receive” — shifts to normative future tense. | ⚠️ Minor temporal nuance change. |
| “That the Rules… shall be as follows” | Introduces forthcoming section. | Compressed into direct declarative of rule content. | ⚠️ Slight formal change, semantics intact. |
| Membership / alternates / term clauses | Normative rules about composition and duration. | Split into clear, one-sentence propositions. | ✅ Same meaning, better granularity. |


#### Semantic Splitting

Proposed model proposes the text. 

And in late chunking, pipeline checks if meaning shift between sentences exists.

Final output via late chunking is :


1. Article 83 of the Treaty establishing the European Economic Community provides for an advisory committee consisting of experts designated by the Governments of Member States. The advisory committee shall be attached to the Commission and consulted on transport matters whenever the Commission considers it desirable. The advisory committee shall not prejudice the powers of the transport section of the Economic and Social Committee.
2. Article 153 of the Treaty provides for the Council to determine the rules governing the committees provided for in that Treaty after receiving an opinion from the Commission. The Council shall receive an Opinion from the Commission. The Rules of the Transport Committee shall consist of experts on transport matters designated by the Governments of Member States. Each Government shall designate one expert or two experts selected from among senior officials of the central administration. Each Government may designate not more than three experts of acknowledged competence in the railway, road transport, and inland waterway sectors. Each Government may designate an alternate for each member of the Committee appointed by it. The alternate shall satisfy conditions the same as those for the member of the Committee whom he replaces.
3. Alternates shall attend Committee meetings and take part in the work of the Committee only in the event of full members being unable to do so. Committee members and their alternates shall be appointed in their personal capacity. Committee members and their alternates may not be bound by any mandatory instructions. The term of office for members and their alternates shall be two years. Appointments for members and their alternates may be renewed. In the event of the death, resignation, or compulsory retirement of a member or alternate, that member or alternate shall be replaced for the remainder of his term of office. The Government which appointed a member or alternate may compulsorily retire that member or alternate only if the member or alternate no longer fulfils the conditions required for the performance of his duties. The Committee shall elect a Chairman and Vice-Chairman from among the members appointed by virtue of their status as senior officials of the central administration. The Chairman and Vice-Chairman shall serve as such for two years. Should the Chairman or Vice-Chairman cease to hold office before the period for which he was elected has expired, a replacement for him shall be elected for the remainder of the period for which he was originally elected. Neither the Chairman nor the Vice-Chairman may be re-elected. The Chairman shall convene the Committee at the request of the Commission whenever the latter wishes to consult it.
4. The Commission's request shall state the purpose of the consultation.
5. When the Committee is consulted by the Commission, it shall present the Commission with a report setting out the conclusions reached as a result of its deliberations. The Committee shall present the Commission with a report if the Commission entrusts it with the study of a specific problem. The Commission shall also be entitled to consult the Committee orally. The minutes of the Committee shall be sent to the Commission. The Commission shall be invited to send its representatives to meetings of the Committee and its working parties. The Committee shall adopt rules of procedure laying down its methods of working. The Committee may seek the assistance of any suitably qualified person, obtain any advice and hold hearings. Such action may be taken only with the consent of the Commission. The expenses of the Committee shall be included in the estimates of the Commission.
6. The President of the Council is L. Erhard.




### Chat Agent

As a framework for thinking/orchestrating AI agents I want to experiment CrewAI.

I've written my own pipelines myself 2 years ago, I've used celery+own implementation on agents at career.io/interview-prep . Tested  but didn't like Langchain 1 year ago for different project. 

At the end of the day they are extension of api-wrappers, nothing wrong with writing 2-3 step agents by yourself but when agents have multistep, orchestration could be better. 

Prompt templating on MongoDB and letting PMs to modify prompts is also a good choice for experimenting, leaving polishing to PMs. 

uv run python -m spacy download en_core_web_sm

### Retriever

Automergingretrieval is used. 


#### Query Enhancement

Before the retrieval layer, query enhancement is applied. 



Automerging retriever heavily advised by Langchain/Milvus. TO DO: Place diagrams .


### Tech Stack for Session Management 
Considerations:
- Reads will be dominant.
- Conversation retrieval should be quick.
- Conversation retrieval can be needed both by backend and frontend.



a. Redis : To keep latest conversations/sessions in-memory and quick recovery.

b. Mongodb : Persistent DB to:
1. Retrieve unused conversation from mongodb to redis, if conversation is reinstantiated
2. Store conversations and other related artifacts (redis keys) which are cache invalidated due to TTL (6 hours, 1 business day, 1 week)

c. Celery : To orchestrate TTLs from redis to mongo.

Pattern : Cache Aside Pattern

App <-> Redis <-> MongoDB 


#### Redis Express 

To test if conversation in redis

'
GET session:0ea95f3a-b0ab-4e2e-92d8-6e227fd7715f

TTL session:0ea95f3a-b0ab-4e2e-92d8-6e227fd7715f
'


Mongodb Atlas (heavily used it before, quite liked it) can be used for tracking, but for simplicity I wanted to use Mongo Express UI.


