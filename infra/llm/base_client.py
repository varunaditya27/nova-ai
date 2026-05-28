# Base LLM Client
#
# Abstract interface that all LLM implementations must follow.
#
# Methods:
#   - complete(prompt: str, **params) -> str
#   - stream(prompt: str, **params) -> AsyncGenerator[str]
#   - get_model_name() -> str
#   - health_check() -> bool
#
# All LLM calls go through one of these implementations.
