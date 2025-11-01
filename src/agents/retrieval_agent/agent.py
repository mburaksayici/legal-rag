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
	) -> tuple[str, list]:
		"""
		Retrieve relevant chunks for a question with optional query enhancement and reranking.
		
		Args:
			question: The user's question
			use_query_enhancer: If True, enhance query with LLM (default: False)
			use_reranking: If True, rerank documents with LLM (default: False)
			top_k: Number of documents to return (default: 10)
		
		Returns:
			Tuple of (context_text, sources_list)
		"""
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
		
		# Collect results from all queries using SimpleQdrantRetriever (pure vector DB)
		all_context_parts = []
		all_sources = []
		seen_texts = set()  # To avoid duplicate content
		
		# If using reranking, retrieve more documents per query
		per_query_multiplier = 2 if use_reranking else 1
		
		for search_query in queries_to_search:
			try:
				# Retrieve more documents if we're going to rerank
				per_query_k = max(4, (top_k // len(queries_to_search)) * per_query_multiplier)
				context_text, sources = self.retriever.retrieve(search_query, top_k=per_query_k)
				print(f"Retrieved {per_query_k} docs for query: {search_query[:50]}...")
				
				if context_text:
					# Split context into parts and deduplicate
					context_parts = context_text.split('\n\n')
					for i, part in enumerate(context_parts):
						part = part.strip()
						if part and part not in seen_texts:
							seen_texts.add(part)
							all_context_parts.append(part)
							# Track corresponding source for each document part
							if i < len(sources):
								all_sources.append(sources[i])
							else:
								all_sources.append("unknown")
					
			except Exception as e:
				print(f"Retrieval failed for query '{search_query}': {e}")
				continue
		
		# Apply reranking if enabled
		if use_reranking and all_context_parts:
			print(f"Reranking {len(all_context_parts)} documents using original query: {question}")
			try:
				final_context, reranked_sources = self.reranker.rerank(
					query=question,  # Use original question, not enhanced queries
					documents=all_context_parts,
					sources=all_sources,
					top_k=top_k
				)
				print(f"Reranked to top {top_k} documents")
				return final_context, reranked_sources
			except Exception as e:
				print(f"Reranking failed, falling back to original order: {e}")
				# Fallback to non-reranked results
		
		# If reranking is disabled or failed, use original ordering
		final_context = "\n\n".join(all_context_parts[:top_k])  # Limit to top_k chunks total
		final_sources = list(dict.fromkeys(all_sources[:top_k]))  # Deduplicate while preserving order
		print(f"Final context (no reranking): {len(all_context_parts[:top_k])} documents")
		return final_context, final_sources

