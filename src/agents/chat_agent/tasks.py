from crewai import Task  # type: ignore


def create_chat_task(agent):
	"""Create a chat task for the agent."""
	return Task(
		description="Answer the user's question: {question}. {context_instruction}",
		agent=agent,
		expected_output="A clear and helpful answer to the question.",
	)

