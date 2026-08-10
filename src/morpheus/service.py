import os
import httpx
import json
from abc import ABC, abstractmethod
from typing import AsyncGenerator

import anthropic
from google import genai
from google.genai import types

from provider import Provider, Configuration, DEFAULT_PROVIDER

class ProviderService(ABC):
    def __init__(self, config: Configuration):
        self.config = config

    @abstractmethod
    def prompt(self, messages: list) -> AsyncGenerator[str, None]:
        pass

class OllamaService(ProviderService):
    async def prompt(self, messages: list) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": True,
            "options": { 
                "temperature": 0.7, 
                "num_predict": 1024
            }
        }

        thinking = False

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", self.config.url, json=payload) as response:
                async for line in response.aiter_lines():
                    if not line: continue
                    try:
                        chunk = json.loads(line)

                        message = chunk.get("message", {})
                        thought = message.get("thinking", "")
                        content = message.get("content", "")

                        if thought and not thinking:
                            yield "[THINKING]"
                            thinking = True

                        if content:
                            if thinking:
                                yield "[RESPONSE]"
                                thinking = False
                            yield content

                    except json.JSONDecodeError:
                        continue

class AnthropicService(ProviderService):
    def __init__(self, config: Configuration):
        super().__init__(config)
        self.client = anthropic.AsyncAnthropic(api_key=self.config.api_key)

    async def prompt(self, messages: list) -> AsyncGenerator[str, None]:
        system_prompt = ""
        user_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_prompt = msg['content']
            else:
                user_messages.append(msg)

        async with self.client.messages.stream(
            max_tokens=1024,
            messages=user_messages,
            system=system_prompt,
            model=self.config.model,
            temperature=0.7
        ) as stream:
            async for text in stream.text_stream:
                yield text
                
class GeminiService(ProviderService):
    def __init__(self, config: Configuration):
        super().__init__(config)
        self.client = genai.Client()

    async def prompt(self, messages: list) -> AsyncGenerator[str, None]:
        system_prompt = ""
        gemini_history = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_prompt = msg['content']
            else:
                # IMPORTANT: Gemini uses "model" instead of "assistant"
                role = "model" if msg['role'] == 'assistant' else "user"
                gemini_history.append({"role": role, "parts": [msg['content']]})

        config = types.GenerateContentConfig(
            system_instruction=system_prompt
        )

        chat = self.client.chats.create(
            model=self.config.model,
            history=gemini_history[:-1],
            config=config
        )

        last_message = gemini_history[-1]["parts"][0]

        response_stream = chat.send_message_stream(last_message)
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text

class Service:
    @staticmethod
    def create(provider: Provider = Provider.DEFAULT, config: Configuration = DEFAULT_PROVIDER[Provider.DEFAULT]) -> ProviderService:
        if provider != Provider.DEFAULT:
            config = DEFAULT_PROVIDER[provider]

        if provider == Provider.OLLAMA:
            return OllamaService(config)

        if provider == Provider.GOOGLE:
            return GeminiService(config)

        raise ValueError(f"Unsupported service type: {provider}")
