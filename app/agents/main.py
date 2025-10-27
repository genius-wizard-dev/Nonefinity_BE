from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver
from app.agents.context import AgentContext
from app.utils import get_logger
from app.agents.llms import LLMConfig
from app.agents.prompts import SYSTEM_PROMPT
from app.agents.context import AgentContext
from langchain_core.tools.base import BaseTool
from typing import List
from langchain.agents.middleware import AgentMiddleware
logger = get_logger(__name__)




async def get_agent(tools: List[BaseTool], llm_config: LLMConfig, middleware: List[AgentMiddleware]):
  return create_agent(
    model=llm_config.get_model(),
    tools=tools,
    middleware=middleware,
    context_schema=AgentContext,
    state_schema=AgentState,
    checkpointer=InMemorySaver(),
    system_prompt=SYSTEM_PROMPT
  )


