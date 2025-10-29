from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver
from app.agents.context import AgentContext
from app.utils import get_logger
from app.agents.llms import LLMConfig
from app.agents.prompts import SYSTEM_PROMPT
from app.agents.context import AgentContext
from langchain_core.tools.base import BaseTool
from typing import List, Dict, Optional
from langchain.agents.middleware import AgentMiddleware
import asyncio
from datetime import datetime, timedelta
import uuid

logger = get_logger(__name__)


class AgentManager:
    """Manages agent instances to avoid recreating them on each request"""

    def __init__(self):
        self._agents: Dict[str, Dict] = {}  # thread_id -> agent_info
        self._cleanup_interval = 300  # 5 minutes
        self._max_idle_time = 1800  # 30 minutes
        self._lock = asyncio.Lock()

    async def get_or_create_agent(
        self,
        thread_id: str,
        tools: List[BaseTool],
        llm_config: LLMConfig,
        middleware: List[AgentMiddleware] = None
    ):
        """Get existing agent or create new one for thread_id"""
        if middleware is None:
            middleware = []

        async with self._lock:
            # Check if agent exists and is still valid
            if thread_id in self._agents:
                agent_info = self._agents[thread_id]
                # Check if agent is not too old
                if datetime.now() - agent_info['created_at'] < timedelta(seconds=self._max_idle_time):
                    agent_info['last_used'] = datetime.now()
                    logger.info(f"Reusing existing agent for thread {thread_id}")
                    return agent_info['agent']
                else:
                    # Remove expired agent
                    logger.info(f"Removing expired agent for thread {thread_id}")
                    del self._agents[thread_id]

            # Create new agent
            logger.info(f"Creating new agent for thread {thread_id}")
            agent = create_agent(
                model=llm_config.get_model(),
                tools=tools,
                middleware=middleware,
                context_schema=AgentContext,
                state_schema=AgentState,
                checkpointer=InMemorySaver(),
                system_prompt=SYSTEM_PROMPT
            )


            self._agents[thread_id] = {
                'agent': agent,
                'created_at': datetime.now(),
                'last_used': datetime.now(),
                'tools': tools,
                'llm_config': llm_config,
                'middleware': middleware
            }

            return agent

    async def get_agent(self, thread_id: str):
        """Get agent for thread_id"""
        async with self._lock:
            if thread_id in self._agents:
                return self._agents[thread_id]['agent']
            else:
                return None

    async def remove_agent(self, thread_id: str):
        """Remove agent for specific thread_id"""
        async with self._lock:
            if thread_id in self._agents:
                del self._agents[thread_id]
                logger.info(f"Removed agent for thread {thread_id}")

    async def cleanup_expired_agents(self):
        """Remove expired agents"""
        async with self._lock:
            current_time = datetime.now()
            expired_threads = []

            for thread_id, agent_info in self._agents.items():
                if current_time - agent_info['last_used'] > timedelta(seconds=self._max_idle_time):
                    expired_threads.append(thread_id)

            for thread_id in expired_threads:
                del self._agents[thread_id]
                logger.info(f"Cleaned up expired agent for thread {thread_id}")



    async def list_active_threads(self) -> List[str]:
        """List all active thread IDs"""
        async with self._lock:
            return list(self._agents.keys())

    def start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_loop():
            while True:
                try:
                    await self.cleanup_expired_agents()
                    await asyncio.sleep(self._cleanup_interval)
                except Exception as e:
                    logger.error(f"Error in cleanup task: {str(e)}")
                    await asyncio.sleep(60)  # Wait 1 minute before retrying

        # Start cleanup task
        asyncio.create_task(cleanup_loop())
        logger.info("Started agent cleanup task")


# Global agent manager instance
agent_manager = AgentManager()

# Start cleanup task when module is imported
agent_manager.start_cleanup_task()





async def get_agent_for_thread(thread_id: str, tools: List[BaseTool], llm_config: LLMConfig, middleware: List[AgentMiddleware] = None):
    """Get agent for specific thread_id"""
    return await agent_manager.get_or_create_agent(thread_id, tools, llm_config, middleware)



async def get_agent(thread_id: str):
    """Get agent for specific thread_id"""
    return await agent_manager.get_agent(thread_id)
