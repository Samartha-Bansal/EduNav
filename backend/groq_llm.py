"""Groq API integration for LlamaIndex."""

import asyncio
import os
from typing import Any, AsyncGenerator, List, Optional

from dotenv import load_dotenv
from groq import Groq
from llama_index.core.llms import (
    ChatMessage,
    CompletionResponse,
    CompletionResponseGen,
    LLM,
    LLMMetadata,
    MessageRole,
)

load_dotenv()


class GroqLLM(LLM):
    model_name: str = "llama-3.1-8b-instant"
    temperature: float = 0.05
    max_tokens: Optional[int] = 2048
    _client: Optional[Groq] = None

    def __init__(
        self,
        model_name: str = "llama-3.1-8b-instant",
        temperature: float = 0.05,
        max_tokens: Optional[int] = 2048,
        api_key: Optional[str] = None,
    ):
        super().__init__()
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY is required")
        self._client = Groq(api_key=key)

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=8192,
            num_output=self.max_tokens or 1024,
            model_name=self.model_name,
        )

    def generate(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens or 1024,
        )
        return response.choices[0].message.content or ""

    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        return CompletionResponse(text=self.generate(prompt))

    async def acomplete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, self.generate, prompt)
        return CompletionResponse(text=text)

    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        yield self.complete(prompt, **kwargs)

    async def astream_complete(self, prompt: str, **kwargs: Any) -> AsyncGenerator[CompletionResponse, None]:
        yield await self.acomplete(prompt, **kwargs)

    def chat(self, messages: List[ChatMessage], **kwargs: Any) -> CompletionResponse:
        groq_messages = []
        for message in messages:
            role = "user" if message.role == MessageRole.USER else "assistant"
            groq_messages.append({"role": role, "content": message.content})
        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=groq_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens or 1024,
        )
        return CompletionResponse(text=response.choices[0].message.content or "")

    async def achat(self, messages: List[ChatMessage], **kwargs: Any) -> CompletionResponse:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.chat(messages, **kwargs))

    def stream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> CompletionResponseGen:
        yield self.chat(messages, **kwargs)

    async def astream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> AsyncGenerator[CompletionResponse, None]:
        yield await self.achat(messages, **kwargs)
