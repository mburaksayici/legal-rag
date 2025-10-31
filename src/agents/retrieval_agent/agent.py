from crewai import Agent  # type: ignore
from langchain_openai import ChatOpenAI  # type: ignore

from src.config import OPENAI_API_KEY
from src.retrieval.simple_chromadb_retriever import SimpleChromaDBRetriever
from src.agents.query_enhancer.agent import QueryEnhancerAgent
from src.embeddings.base import BaseEmbedding as CustomBaseEmbedding


class RetrievalAgent:
	def __init__(self, embedding: CustomBaseEmbedding, use_query_enhancer: bool = True):
		self.embedding = embedding
		self.use_query_enhancer = use_query_enhancer
		self.retriever = SimpleChromaDBRetriever(embedding=embedding)
		self.query_enhancer = QueryEnhancerAgent() if use_query_enhancer else None
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

	def retrieve(self, question: str) -> tuple[str, list]:
		"""Retrieve relevant chunks for a question with query enhancement. Returns (context_text, sources_list)."""
		
		# Enhance query if query enhancer is available
		queries_to_search = [question]  # Always include original
		if self.query_enhancer is not None:
			try:
				enhanced_queries = self.query_enhancer.enhance_query(question)
				# Use enhanced queries, but limit total queries to avoid too many API calls
				queries_to_search = enhanced_queries[:3]  # Use top 3 enhanced queries
				print(f"Enhanced queries: {queries_to_search}")
			except Exception as e:
				print(f"Query enhancement failed, using original query: {e}")
				queries_to_search = [question]
		
		# Collect results from all queries
		all_context_parts = []
		all_sources = set()
		seen_texts = set()  # To avoid duplicate content
		
		for search_query in queries_to_search:
			try:
				# Use smaller top_k per query since we're doing multiple queries
				per_query_k = max(2, 6 // len(queries_to_search))
				context_text, sources = self.retriever.retrieve(search_query, top_k=per_query_k)
				print(f"Context text: {context_text}")
				print(f"Sources: {sources}")
				if context_text:
					# Split context into parts and deduplicate
					context_parts = context_text.split('\n\n')
					for part in context_parts:
						part = part.strip()
						if part and part not in seen_texts:
							seen_texts.add(part)
							all_context_parts.append(part)
					
					# Add sources
					all_sources.update(sources)
					
			except Exception as e:
				print(f"Retrieval failed for query '{search_query}': {e}")
				continue
		
		# Limit total results and join
		final_context = "\n\n".join(all_context_parts[:6])  # Limit to 6 chunks total
		print(f"Final context: {final_context}")
		print(f"Final sources: {list(all_sources)}")
		return final_context, list(all_sources)

