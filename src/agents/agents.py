from .chat_agent.agent import ChatAgent

# Registry of all available agents
AVAILABLE_AGENTS = {
	"chat_agent": ChatAgent,
}

def get_agent(agent_name: str):
	"""Get an agent instance by name."""
	if agent_name not in AVAILABLE_AGENTS:
		raise ValueError(f"Unknown agent: {agent_name}. Available: {list(AVAILABLE_AGENTS.keys())}")
	return AVAILABLE_AGENTS[agent_name]()

