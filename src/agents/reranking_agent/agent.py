from typing import List, Tuple
from crewai import Agent, LLM  # type: ignore
from langchain_openai import ChatOpenAI  # type: ignore

from src.config import OPENAI_API_KEY
from src.agents.schemas import RerankedResults


class RerankingAgent:
	"""Agent that reranks retrieved documents based on relevance to the original query."""
	
	def __init__(self):
		self.agent = Agent(
			role="Legal Document Relevance Analyst",
			goal="Accurately assess and rank the relevance of legal documents to user queries",
			backstory="""You are an expert legal analyst specializing in European Union legislation. 
			Your role is to evaluate how relevant each document is to a user's question, considering 
			legal context, terminology, and the specific information needs of legal research.""",
			llm=self._create_llm(),
			verbose=True,
			allow_delegation=False,
		)
	
	def _create_llm(self):
		return ChatOpenAI(
			model="gpt-4o-mini",
			temperature=0.1,  # Very low temperature for consistent relevance scoring
			openai_api_key=OPENAI_API_KEY,
		)
	
	def rerank(
		self, 
		query: str, 
		documents: List[str], 
		sources: List[str] = None,
		top_k: int = 10
	) -> Tuple[str, List[str]]:
		"""
		Rerank documents based on relevance to the original user query.
		
		Args:
			query: The original user question (not enhanced queries)
			documents: List of retrieved document texts
			sources: List of document sources (optional, parallel to documents)
			top_k: Number of top documents to return after reranking
		
		Returns:
			Tuple of (context_text, sources_list) with reranked top_k documents
		"""
		if not documents:
			return "", []
		
		# Limit documents to rerank (avoid very long prompts)
		max_docs_to_rerank = min(len(documents), 20)
		documents_to_rank = documents[:max_docs_to_rerank]
		sources_to_rank = sources[:max_docs_to_rerank] if sources else [f"doc_{i}" for i in range(max_docs_to_rerank)]
		
		# Build the reranking prompt
		reranking_prompt = self._build_reranking_prompt(query, documents_to_rank)
		
		try:
			# Use CrewAI's structured LLM output
			llm = LLM(model="gpt-4o-mini", api_key=OPENAI_API_KEY, response_format=RerankedResults)
			
			response = llm.call(reranking_prompt)
			
			# Extract ranked documents from structured response
			if hasattr(response, 'ranked_documents') and isinstance(response.ranked_documents, list):
				ranked_docs = response.ranked_documents
				
				# Sort by relevance score (highest first)
				ranked_docs.sort(key=lambda x: x.relevance_score, reverse=True)
				
				# Get top_k documents
				top_ranked = ranked_docs[:top_k]
				
				# Build context and sources from reranked results
				reranked_context_parts = []
				reranked_sources = []
				
				for ranked_doc in top_ranked:
					idx = ranked_doc.index
					if 0 <= idx < len(documents_to_rank):
						reranked_context_parts.append(documents_to_rank[idx])
						reranked_sources.append(sources_to_rank[idx])
				
				print(f"Reranked {len(reranked_context_parts)} documents (from {len(documents_to_rank)} total)")
				
				return "\n\n".join(reranked_context_parts), reranked_sources
			else:
				print(f"Invalid reranking response format: {response}")
				# Fallback to original order
				return "\n\n".join(documents_to_rank[:top_k]), sources_to_rank[:top_k]
			
		except Exception as e:
			print(f"Reranking failed: {e}")
			# Fallback to original order
			return "\n\n".join(documents_to_rank[:top_k]), sources_to_rank[:top_k]
	
	def _build_reranking_prompt(self, query: str, documents: List[str]) -> str:
		"""Build the prompt for document reranking."""
		
		# Format documents with indices
		formatted_docs = []
		for i, doc in enumerate(documents):
			# Truncate very long documents for the prompt
			doc_preview = doc[:500] + "..." if len(doc) > 500 else doc
			formatted_docs.append(f"Document {i}:\n{doc_preview}")
		
		docs_text = "\n\n".join(formatted_docs)
		
		prompt = f"""You are analyzing legal documents for relevance to a user's question about European legislation.

User's Question: "{query}"

Documents to Rank:
{docs_text}

Your Task:
1. Carefully evaluate how relevant each document is to answering the user's question
2. Consider:
   - Direct relevance to the question topic
   - Presence of key legal concepts, terms, or frameworks mentioned in the query
   - Quality and specificity of information provided
   - Whether the document actually helps answer the question
3. Assign each document a relevance score from 0.0 to 10.0, where:
   - 10.0 = Perfectly relevant, directly answers the question
   - 7.0-9.0 = Highly relevant, contains important information
   - 4.0-6.0 = Moderately relevant, contains some useful context
   - 1.0-3.0 = Minimally relevant, tangentially related
   - 0.0 = Not relevant at all

Return a relevance score for each document based on the document index (0 to {len(documents)-1})."""

		return prompt

