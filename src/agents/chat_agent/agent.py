from typing import Optional

from crewai import Agent  # type: ignore

from src.config import OPENAI_API_KEY


class ChatAgent:
	def __init__(self):
		self.agent = Agent(
			role="Legal Research Assistant",
			goal="Answer user questions accurately using retrieved documents with proper citations",
			backstory="""You are a legal research assistant specializing in European Union legislation and regulations. 
When answering questions:
1. Use ONLY information from the provided context
2. Cite each source with a unique number: [1], [2], [3], etc.
3. Each citation number should correspond to a specific source document
4. List all cited sources at the end with their document paths
5. If the context doesn't contain relevant information, say so clearly
6. Be concise but thorough in your explanations""",
			llm=self._create_crewai_llm(),
			verbose=True,
		)

	def _create_crewai_llm(self):
		from langchain_openai import ChatOpenAI  # type: ignore
		return ChatOpenAI(
			model="gpt-4o-mini",
			temperature=0.7,
			openai_api_key=OPENAI_API_KEY,
		)

	def answer(self, question: str, context: Optional[str] = None) -> str:
		"""Answer a question using the agent."""
		if context:
			prompt = f"Context: {context}\n\nQuestion: {question}\n\nAnswer:"
		else:
			prompt = f"Question: {question}\n\nAnswer:"
		result = self.agent.execute(prompt)
		return str(result) if result else "I couldn't generate an answer."

