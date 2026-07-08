from abc import ABC, abstractmethod
from typing import AsyncGenerator

from src.api.config import get_settings

settings = get_settings()


class LLMClient(ABC):
    @abstractmethod
    async def stream(self, system_prompt: str, user_query: str) -> AsyncGenerator[str, None]:
        ...

    @abstractmethod
    async def stream_complete(self, prompt: str) -> AsyncGenerator[str, None]:
        ...




    async def stream_complete(self, prompt: str) -> AsyncGenerator[str, None]:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key)
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicProvider(LLMClient):
    def __init__(self, api_key: str = "", model: str = "claude-3-haiku-20240307"):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model

    async def stream(self, system_prompt: str, user_query: str) -> AsyncGenerator[str, None]:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=self.api_key)
        async with client.messages.stream(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_query}],
            max_tokens=4096,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def stream_complete(self, prompt: str) -> AsyncGenerator[str, None]:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=self.api_key)
        async with client.messages.stream(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        ) as stream:
            async for text in stream.text_stream:
                yield text


class GroqProvider(LLMClient):
    def __init__(self, api_key: str = "", model: str = "llama3-8b-8192"):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model

    async def stream(self, system_prompt: str, user_query: str) -> AsyncGenerator[str, None]:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key, base_url="https://api.groq.com/openai/v1")
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def stream_complete(self, prompt: str) -> AsyncGenerator[str, None]:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key, base_url="https://api.groq.com/openai/v1")
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


def get_llm_client() -> LLMClient:
    provider = settings.LLM_PROVIDER.lower()
    if provider == "anthropic":
        return AnthropicProvider()
    elif provider == "groq":
        return GroqProvider()
    return OpenAIProvider()
