class AgentError(Exception):
    """Base exception for DataPilot-AI agent failures."""


class IntentClassificationError(AgentError):
    """Raised when the agent cannot classify a user request."""


class AgentRoutingError(AgentError):
    """Raised when the agent cannot route a classified request."""


class AgentExecutionError(AgentError):
    """Raised when an agent specialist node fails."""
