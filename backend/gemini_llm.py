from google import genai
from llama_index.core.llms import LLM, CompletionResponse, CompletionResponseGen
from llama_index.core.llms import ChatMessage, MessageRole
from typing import Any, List, Optional, AsyncGenerator
import os
from dotenv import load_dotenv
import asyncio
from llama_index.core.llms import LLMMetadata
# Load environment variables
load_dotenv()

class GeminiLLM(LLM):
    """
    Custom LLM class for Google Gemini integration with LlamaIndex using the new google.genai SDK
    """

    model_name: str = "gemini-2.0-flash"
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    client: Optional[Any] = None

    def __init__(self, model_name: str = "gemini-3-flash-preview", temperature: float = 0.1, max_tokens: Optional[int] = None):
        super().__init__()
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Load API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        # Initialize the new Google Gen AI client
        self.client = genai.Client(api_key=api_key)

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=8192,
            num_output=256,
            model_name=self.model_name
        )
    def generate(self, prompt: str) -> str:
        """
        Generate a response from the prompt using Gemini.
        Returns the text response directly.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """Complete a prompt using Gemini (LlamaIndex compatibility)"""
        try:
            text = self.generate(prompt)
            return CompletionResponse(text=text)
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

    async def acomplete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """Async complete a prompt using Gemini"""
        # For simplicity, run sync method in thread pool
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, self.generate, prompt)
        return CompletionResponse(text=text)

    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        """Streaming completion (not implemented for simplicity)"""
        response = self.complete(prompt, **kwargs)
        yield response

    async def astream_complete(self, prompt: str, **kwargs: Any) -> AsyncGenerator[CompletionResponse, None]:
        """Async streaming completion"""
        response = await self.acomplete(prompt, **kwargs)
        yield response

    def chat(self, messages: List[ChatMessage], **kwargs: Any) -> CompletionResponse:
        """Chat completion using Gemini"""
        try:
            # Convert LlamaIndex messages to Gemini format
            contents = []
            for message in messages:
                role = "user" if message.role == MessageRole.USER else "model"
                contents.append(genai.Content(role=role, parts=[genai.Part(text=message.content)]))

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents
            )

            return CompletionResponse(text=response.text)

        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

    async def achat(self, messages: List[ChatMessage], **kwargs: Any) -> CompletionResponse:
        """Async chat completion using Gemini"""
        # For simplicity, run sync method in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.chat, messages)
        return result

    def stream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> CompletionResponseGen:
        """Streaming chat (not implemented for simplicity)"""
        response = self.chat(messages, **kwargs)
        yield response

    async def astream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> AsyncGenerator[CompletionResponse, None]:
        """Async streaming chat"""
        response = await self.achat(messages, **kwargs)
        yield response