import httpx
import json
from abc import ABC, abstractmethod
from typing import AsyncGenerator

class LLMProvider(ABC):
    @abstractmethod
    def stream_chat(self, messages: list) -> AsyncGenerator[str, None]:
        pass

class OllamaProvider(LLMProvider):
    def __init__(self, model: str, url: str = "http://localhost:11434/api/chat"):
        self.model = model
        self.url = url

    async def stream_chat(self, messages: list) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.7, "num_predict": 1024}
        }

        # STATE TRACKER: Keeps track of whether we have already announced the thinking phase
        thinking_active = False

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", self.url, json=payload) as response:
                async for line in response.aiter_lines():
                    if not line: continue
                    try:
                        chunk = json.loads(line)
                        message = chunk.get("message", {})
                        thinking = message.get("thinking", "")
                        content = message.get("content", "")

                        # --- HANDLE THINKING PHASE ---
                        if thinking:
                            if not thinking_active:
                                # Only yield the header ONCE at the very start
                                yield "\n[ANALYSIS]: "
                                thinking_active = True
                            yield thinking

                        # --- HANDLE CONTENT PHASE ---
                        if content:
                            if thinking_active:
                                # Transition from Thinking -> Speaking
                                yield "\n\n[RESPONSE]:\n"
                                thinking_active = False # Reset state
                            yield content

                    except json.JSONDecodeError:
                        continue
