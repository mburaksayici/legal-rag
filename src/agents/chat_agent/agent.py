from typing import Optional

from crewai import Agent  # type: ignore

from src.config import OPENAI_API_KEY


class ChatAgent:
	def __init__(self):
		self.agent = Agent(
			role="Assistant",
			goal="Answer user questions accurately and helpfully",
			backstory="You are a helpful AI assistant that answers questions using available knowledge.",
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

