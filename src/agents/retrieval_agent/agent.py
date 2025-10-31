from crewai import Agent  # type: ignore
from langchain_openai import ChatOpenAI  # type: ignore
from llama_index.core import StorageContext, VectorStoreIndex  # type: ignore

from src.config import OPENAI_API_KEY
from src.retrieval.auto_merging_retriever import AutoMergingRetrieverWrapper
from src.retrieval.storage_setup import StorageSetup
from src.embeddings.base import BaseEmbedding as CustomBaseEmbedding


class RetrievalAgent:
	def __init__(self, storage_context: StorageContext, embedding: CustomBaseEmbedding):
		self.storage_context = storage_context
		self.embedding = embedding
		self.retriever = self._create_retriever()
		self.agent = Agent(
			role="Research Assistant",
			goal="Answer user questions accurately by retrieving relevant information from the database and providing citations",
			backstory="You are a helpful research assistant that answers questions using retrieved documents. Always cite your sources.",
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

	def _create_retriever(self) -> AutoMergingRetrieverWrapper:
		"""Create AutoMergingRetriever from storage_context."""
		storage_setup = StorageSetup(embedding=self.embedding)
		# Rebuild index from storage_context vector store
		breakpoint()
		embed_adapter = storage_setup.create_embedding_adapter()
		index = VectorStoreIndex.from_vector_store(
			vector_store=self.storage_context.vector_store,
			storage_context=self.storage_context,
			embed_model=embed_adapter,
		)
		return AutoMergingRetrieverWrapper(
			index=index,
			storage_context=self.storage_context,
			similarity_top_k=6,
		)

	def retrieve(self, question: str) -> tuple[str, list]:
		breakpoint()
		"""Retrieve relevant chunks for a question. Returns (context_text, sources_list)."""
		response = self.retriever.retrieve(question)
		context_parts = []
		sources = set()
		for result in response.results:
			context_parts.append(result.text)
			if result.source:
				sources.add(result.source)
		return "\n\n".join(context_parts), list(sources)

