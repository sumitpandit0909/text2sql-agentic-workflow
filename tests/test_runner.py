import asyncio
from app.services.runner_service import stream_agent_reply
from app.core.observability import setup_observability
setup_observability()

async def main():
    async for chunk in stream_agent_reply("test_user2", "test_session2", "How many orders were placed in 2024?"):
        print(chunk, end="", flush=True)

asyncio.run(main())