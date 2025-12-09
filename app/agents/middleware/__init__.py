from langchain.agents.middleware import AgentMiddleware
from langchain.messages import RemoveMessage
from langchain.agents import AgentState
from app.agents.types import AgentContext
from langchain.tools import ToolRuntime
from app.crud import chat_message_crud
from app.models.chat import ChatMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from typing import Any
import json
from app.utils import get_logger
from langchain.agents.middleware import SummarizationMiddleware
from langchain.chat_models import init_chat_model
from app.configs.settings import settings
from langchain.chat_models.base import BaseChatModel

logger = get_logger(__name__)
class NonfinityAgentMiddleware(AgentMiddleware):

    def _extract_text_from_content(self, raw_content: Any) -> str:
      """Normalize stored message content to a plain string.

      Handles cases where content is:
      - a JSON-encoded list of segments like [{"type":"text","text":"..."}]
      - a plain JSON-encoded string
      - already a plain string
      """
      if raw_content is None:
          return ""

      # If already a list/dict (unlikely from DB), handle directly
      if isinstance(raw_content, list):
          try:
              return "".join(
                  segment.get("text", "")
                  for segment in raw_content
                  if isinstance(segment, dict) and segment.get("type") == "text"
              )
          except Exception:
              return json.dumps(raw_content, ensure_ascii=False)

      if not isinstance(raw_content, str):
          return str(raw_content)

      # Try parse JSON
      try:
          parsed = json.loads(raw_content)
          if isinstance(parsed, list):
              return "".join(
                  segment.get("text", "")
                  for segment in parsed
                  if isinstance(segment, dict) and segment.get("type") == "text"
              )
          if isinstance(parsed, dict) and "text" in parsed:
              return str(parsed.get("text", ""))
          if isinstance(parsed, (int, float)):
              return str(parsed)
          if isinstance(parsed, str):
              return parsed
          # Fallback to JSON string to preserve info
          return json.dumps(parsed, ensure_ascii=False)
      except Exception:
          # Not JSON, treat as plain string
          return raw_content


    def _convert_chat_message_to_langchain_message(self, chat_message: ChatMessage) -> BaseMessage:
      """Convert stored ChatMessage to a LangChain BaseMessage.

      We only feed user/assistant textual content into history.
      Tool calls/results are already persisted in DB but aren't part of the core
      language history for most models, so they're ignored here.
      """
      role = (chat_message.role or "").lower()
      content = self._extract_text_from_content(chat_message.content)

      if role == "user":
          return HumanMessage(content=content)
      elif role in ("assistant", "ai", "ai_result"):
          return AIMessage(content=content)
      elif role in ("system",):
          return SystemMessage(content=content)
      # For tool messages, include as a tool message with best-effort content
      elif role in ("tool", "tool_result", "tool_calls"):
          return ToolMessage(content=content, name=getattr(chat_message, "name", None))
      # Default to human if unknown
      return HumanMessage(content=content)


    async def abefore_agent(self, state: AgentState, runtime: ToolRuntime[AgentContext, AgentState]) -> dict[str, Any] | None:
        session_id = runtime.context.session_id
        msg = state["messages"]
        recent_messages = await chat_message_crud.model.find(
            {"session_id": session_id, "owner_id": runtime.context.user_id}
        ).sort("-created_at").limit(15).to_list()
        recent_messages.reverse()
        formatted_messages = [self._convert_chat_message_to_langchain_message(msg) for msg in recent_messages]
        new_messages = [*formatted_messages, *msg]
        return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }






def create_summary_middleware(llm: BaseChatModel, config: dict) -> SummarizationMiddleware:
    """
    Create summarization middleware with dynamic config.
    config should be the dictionary under the 'summary' key, e.g. {"model_id": ..., "prompt": ...}
    """
    # Defaults
    max_tokens = int(config.get("max_tokens_before_summary", 4000))
    messages_to_keep = int(config.get("max_message_to_keep", 10))
    prompt = config.get("prompt", "You are a helpful assistant that summarizes the conversation history into a concise summary.")

    return SummarizationMiddleware(
        model=llm,
        max_tokens_before_summary=max_tokens,
        messages_to_keep=messages_to_keep,
        summary_prompt=prompt,
    )



