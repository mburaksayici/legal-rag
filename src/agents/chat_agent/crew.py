from typing import Optional
from crewai import Crew  # type: ignore

from .agent import ChatAgent
from .tasks import create_chat_task
from src.agents.retrieval_agent.agent import RetrievalAgent
from src.embeddings.base import BaseEmbedding as CustomBaseEmbedding
from src.data_preprocess_pipelines.data_preprocess import data_preprocess_semantic_pipeline


class ChatCrew:
	def __init__(self, embedding: Optional[CustomBaseEmbedding] = None, use_query_enhancer: bool = True, use_reranking: bool = True):
		"""Initialize ChatCrew. Uses RetrievalAgent with query enhancement and reranking."""
		self.agent = ChatAgent()
		
		# Get embedding from pipeline if not provided
		if embedding is None:
			embedding = data_preprocess_semantic_pipeline.embedding
		
		# Initialize retrieval agent (agents initialized but not used unless requested in retrieve())
		self.retrieval_agent = None
		self.use_query_enhancer = use_query_enhancer
		self.use_reranking = use_reranking
		if embedding is not None:
			self.retrieval_agent = RetrievalAgent(embedding=embedding)
		
		self.crew = Crew(
			agents=[self.agent.agent],
			tasks=[create_chat_task(self.agent.agent)],
			verbose=True,
		)

	def chat(self, question: str, context: Optional[str] = None) -> tuple[str, list[str]]:
		"""Run chat crew with question. Uses RetrievalAgent with query enhancement and reranking.
		
		Returns:
			tuple: (answer, sources) where sources is a list of document source identifiers
		"""
		# Use retrieval agent to get context for the question (with query enhancement and reranking)
		retrieved_context = None
		sources = []
		if self.retrieval_agent is not None:
			try:
				# retrieve() returns a list of dicts with keys: text, source, score, metadata
				retrieved_docs = self.retrieval_agent.retrieve(
					question=question,
					use_query_enhancer=self.use_query_enhancer,
					use_reranking=self.use_reranking
				)
				if retrieved_docs:
					# Extract text and sources from the retrieved documents
					sources = [doc["source"] for doc in retrieved_docs]
					
					# Format context with numbered sources for proper citation
					context_parts = []
					for i, doc in enumerate(retrieved_docs, 1):
						context_parts.append(f"[Source {i}] from {doc['source']}:\n{doc['text']}")
					
					context_text = "\n\n---\n\n".join(context_parts)
					
					# Add source list at the end
					sources_list = "\n".join([f"[{i}] {source}" for i, source in enumerate(sources, 1)])
					retrieved_context = f"Retrieved Documents:\n\n{context_text}\n\nAvailable Sources:\n{sources_list}"
					print(f"Retrieved {len(sources)} sources for chat")
			except Exception as e:
				# If retrieval fails, continue without context
				print(f"Warning: Retrieval failed: {e}")
		
		# Use provided context or retrieved context
		final_context = context or retrieved_context
		context_instruction = f"Use this context if relevant: {final_context}" if final_context else "No additional context provided."
		
		inputs = {"question": question, "context_instruction": context_instruction}
		result = self.crew.kickoff(inputs=inputs)
		answer = str(result)
		
		# Return answer and sources separately (don't append to answer text)
		return answer, sources

