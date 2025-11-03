from crewai import Task  # type: ignore


def create_chat_task(agent):
	"""Create a chat task for the agent."""
	return Task(
		description="""Answer the user's question: {question}

{context_instruction}

IMPORTANT: 
- Use unique citation numbers [1], [2], [3] for different sources
- Each fact should cite its specific source document
- List all cited sources at the end
- Be accurate and cite every claim""",
		agent=agent,
		expected_output="A well-cited answer with numbered references matching specific source documents",
	)

