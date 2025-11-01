from langchain.agents.middleware import AgentMiddleware
from langchain.agents import create_agent, AgentState
from app.agents.context import AgentContext
from typing import Any
from langchain_core.runnables.config import Runtime
class NonfinityAgentMiddleware(AgentMiddleware):

    def before_agent(self, state: AgentState, runtime: Runtime[AgentContext]) -> dict[str, Any] | None:
        context = runtime.context


