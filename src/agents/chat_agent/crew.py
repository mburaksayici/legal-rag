from typing import Optional
from crewai import Crew  # type: ignore

from .agent import ChatAgent
from .tasks import create_chat_task
from src.retrieval.simple_chromadb_retriever import SimpleChromaDBRetriever
from src.embeddings.base import BaseEmbedding as CustomBaseEmbedding
from src.data_preprocess_pipelines.data_preprocess import data_preprocess_semantic_pipeline


class ChatCrew:
	def __init__(self, embedding: Optional[CustomBaseEmbedding] = None):
		"""Initialize ChatCrew. Uses simple ChromaDB retriever."""
		self.agent = ChatAgent()
		
		# Get embedding from pipeline if not provided
		if embedding is None:
			embedding = data_preprocess_semantic_pipeline.embedding
		
		# Initialize retriever - works with existing ChromaDB data
		self.retriever = None
		if embedding is not None:
			self.retriever = SimpleChromaDBRetriever(embedding=embedding)
		
		self.crew = Crew(
			agents=[self.agent.agent],
			tasks=[create_chat_task(self.agent.agent)],
			verbose=True,
		)

	def chat(self, question: str, context: Optional[str] = None) -> str:
		"""Run chat crew with question. Uses simple ChromaDB retriever for context."""
		# Use simple retriever to get context for the question
		retrieved_context = None
		sources = []
		if self.retriever is not None and self.retriever.is_available():
			try:
				context_text, sources = self.retriever.retrieve(question)
				if context_text:
					retrieved_context = f"Retrieved Context:\n{context_text}"
			except Exception as e:
				# If retrieval fails, continue without context
				print(f"Warning: Retrieval failed: {e}")
		
		# Use provided context or retrieved context
		final_context = context or retrieved_context
		context_instruction = f"Use this context if relevant: {final_context}" if final_context else "No additional context provided."
		
		inputs = {"question": question, "context_instruction": context_instruction}
		result = self.crew.kickoff(inputs=inputs)
		answer = str(result)
		
		# Append citations if sources were retrieved
		if sources:
			citations = "\n\n---\n**Citations:**\n" + "\n".join([f"- {source}" for source in sources])
			answer += citations
		
		return answer

