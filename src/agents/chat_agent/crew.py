from typing import Optional
from crewai import Crew  # type: ignore
from .agent import ChatAgent
from .tasks import create_chat_task


class ChatCrew:
	def __init__(self):
		self.agent = ChatAgent()
		self.crew = Crew(
			agents=[self.agent.agent],
			tasks=[create_chat_task(self.agent.agent)],
			verbose=True,
		)

	def chat(self, question: str, context: Optional[str] = None) -> str:
		"""Run chat crew with question."""
		context_instruction = f"Use this context if relevant: {context}" if context else "No additional context provided."
		inputs = {"question": question, "context_instruction": context_instruction}
		result = self.crew.kickoff(inputs=inputs)
		return str(result)

