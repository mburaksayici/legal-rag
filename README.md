

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

| Topic | Details / Notes |
|--------|-----------------|
| **API vs Self-Hosted** | — |
| **Scaling** | Use **API** to avoid dealing with scaling; **Self-hosted** preferred for small projects. |
| **Personal Note** | “Confession — I'm a little bit weak on that.” |
| **Industry Dependence** | Depends on **data protection standards** in the target industry. |
| **Chosen Stack** | Using **Milvus**, which supports both **local and cloud** setups. |
| **Side Note** | Waiting for **MongoDB** to release full **vector DB** support (currently only available in **Atlas Vector DB** on cloud). |
