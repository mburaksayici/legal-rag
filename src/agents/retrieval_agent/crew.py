from crewai import Crew, Task  # type: ignore
from llama_index.core import StorageContext  # type: ignore
from langchain_openai import ChatOpenAI  # type: ignore

from .agent import RetrievalAgent
from src.config import OPENAI_API_KEY
from src.embeddings.base import BaseEmbedding as CustomBaseEmbedding


class RetrievalCrew:
	def __init__(self, storage_context: StorageContext, embedding: CustomBaseEmbedding):
		self.retrieval_agent_obj = RetrievalAgent(storage_context=storage_context, embedding=embedding)
		self.crew = Crew(
			agents=[self.retrieval_agent_obj.agent],
			tasks=[self._create_task()],
			verbose=True,
		)

	def _create_task(self) -> Task:
		"""Create task that retrieves and answers with citations."""
		return Task(
			description="""Answer the user's question: {question}.

First, retrieve relevant information from the database.
Then, answer the question based on the retrieved context.
At the end, provide citations in the format: [Source: <filename>] for each source used.""",
			agent=self.retrieval_agent_obj.agent,
			expected_output="A clear answer to the question with citations at the end in format [Source: <filename>]",
		)

	def answer_with_citations(self, question: str) -> str:
		"""Simple function: get question, retrieve, return answer with citations."""
		# Retrieve context and sources
		context_text, sources = self.retrieval_agent_obj.retrieve(question)
		
		# Format citations
		citations = "\n\nCitations:\n" + "\n".join([f"[Source: {s}]" for s in sources]) if sources else ""
		
		# Get answer from agent
		answer_prompt = f"""Based on the following context, answer the question: {question}

Context:
{context_text}

Provide a clear, accurate answer based on the context above. Do not make up information not found in the context."""
		
		# Use agent directly to get answer
		llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, openai_api_key=OPENAI_API_KEY)
		response = llm.invoke(answer_prompt)
		answer = response.content if hasattr(response, 'content') else str(response)
		
		return answer + citations

