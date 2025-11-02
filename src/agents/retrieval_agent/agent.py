from crewai import Agent  # type: ignore
from langchain_openai import ChatOpenAI  # type: ignore

from src.config import OPENAI_API_KEY
from src.retrieval.simple_qdrant_retriever import SimpleQdrantRetriever
from src.agents.query_enhancer.agent import QueryEnhancerAgent
from src.agents.reranking_agent.agent import RerankingAgent
from src.embeddings.base import BaseEmbedding as CustomBaseEmbedding


class RetrievalAgent:
	def __init__(self, embedding: CustomBaseEmbedding):
		"""Initialize RetrievalAgent. Agents are always initialized, use controlled via retrieve() parameters."""
		self.embedding = embedding
		self.retriever = SimpleQdrantRetriever(embedding=embedding)
		# Always initialize agents (they're lightweight)
		self.query_enhancer = QueryEnhancerAgent()
		self.reranker = RerankingAgent()
		self.agent = Agent(
			role="Legal Research Assistant",
			goal="Answer user questions accurately by retrieving relevant information from European legal documents and providing citations",
			backstory="You are a legal research assistant specializing in European Union legislation, directives, and regulations. You retrieve relevant legal documents and always cite your sources.",
			llm=self._create_llm(),
			verbose=True,
			allow_delegation=False,
		)

	def _create_llm(self):
		return ChatOpenAI(
			model="gpt-4o-mini",
			temperature=0.7,
			openai_api_key=OPENAI_API_KEY,
		)

	def retrieve(
		self, 
		question: str, 
		use_query_enhancer: bool = False,
		use_reranking: bool = False,
		top_k: int = 10
	) -> list[dict]:
		"""
		Retrieve relevant chunks for a question with optional query enhancement and reranking.
		
		Args:
			question: The user's question
			use_query_enhancer: If True, enhance query with LLM (default: False)
			use_reranking: If True, rerank documents with LLM (default: False)
			top_k: Number of documents to return (default: 10)
		
		Returns:
			List of dicts with keys: text, source, score, metadata
			Note: Scores are only available when both use_query_enhancer and use_reranking are False
		"""
		# If no LLM features, just use direct retrieval with scores
		if not use_query_enhancer and not use_reranking:
			return self.retriever.retrieve(query=question, top_k=top_k)
		
		# Otherwise, use LLM features (query enhancement and/or reranking)
		# Determine queries to search
		queries_to_search = [question]  # Always include original
		if use_query_enhancer:
			try:
				enhanced_queries = self.query_enhancer.enhance_query(question)
				# Use enhanced queries, but limit total queries to avoid too many API calls
				queries_to_search = enhanced_queries[:3]  # Use top 3 enhanced queries
				print(f"Enhanced queries: {queries_to_search}")
			except Exception as e:
				print(f"Query enhancement failed, using original query: {e}")
				queries_to_search = [question]
		
		# Collect results from all queries using SimpleQdrantRetriever
		all_documents = []
		seen_texts = set()  # To avoid duplicate content
		
		# If using reranking, retrieve more documents per query
		per_query_multiplier = 2 if use_reranking else 1
		
		for search_query in queries_to_search:
			try:
				# Retrieve more documents if we're going to rerank
				per_query_k = max(4, (top_k // len(queries_to_search)) * per_query_multiplier)
				detailed_results = self.retriever.retrieve(query=search_query, top_k=per_query_k)
				print(f"Retrieved {per_query_k} docs for query: {search_query[:50]}...")
				
				# Deduplicate by text content
				for doc in detailed_results:
					if doc["text"] not in seen_texts:
						seen_texts.add(doc["text"])
						all_documents.append(doc)
					
			except Exception as e:
				print(f"Retrieval failed for query '{search_query}': {e}")
				continue
		
		if not all_documents:
			return []
		
		# Apply reranking if enabled
		if use_reranking:
			print(f"Reranking {len(all_documents)} documents using original query: {question}")
			try:
				# Extract texts and sources for reranking
				texts = [doc["text"] for doc in all_documents]
				sources = [doc["source"] for doc in all_documents]
				
				final_context, reranked_sources = self.reranker.rerank(
					query=question,  # Use original question, not enhanced queries
					documents=texts,
					sources=sources,
					top_k=top_k
				)
				print(f"Reranked to top {top_k} documents")
				
				# Convert reranked results back to detailed format (without scores)
				reranked_texts = [doc.strip() for doc in final_context.split('\n\n') if doc.strip()]
				results = []
				for i, text in enumerate(reranked_texts[:top_k]):
					results.append({
						"text": text,
						"source": reranked_sources[i] if i < len(reranked_sources) else "unknown",
						"score": None,  # Scores not available after reranking
						"metadata": {"enhanced": use_query_enhancer, "reranked": True}
					})
				return results
				
			except Exception as e:
				print(f"Reranking failed, falling back to original order: {e}")
				# Fallback to non-reranked results
		
		# If reranking is disabled or failed, use original ordering
		results = all_documents[:top_k]
		# Update metadata to indicate processing
		for doc in results:
			doc["score"] = None  # Clear scores when using query enhancement
			doc["metadata"] = {"enhanced": use_query_enhancer, "reranked": False}
		
		print(f"Final results (no reranking): {len(results)} documents")
		return results

	def is_available(self) -> bool:
		"""Check if the retriever is available."""
		return self.retriever.is_available()

