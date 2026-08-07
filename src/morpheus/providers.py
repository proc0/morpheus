import httpx
import json
from abc import ABC, abstractmethod
from typing import AsyncGenerator
import anthropic
import google.generativeai as genai 

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
                                yield "[THINKING]"
                                thinking_active = True
                            # yield thinking

                        # --- HANDLE CONTENT PHASE ---
                        if content:
                            if thinking_active:
                                # Transition from Thinking -> Speaking
                                yield "[RESPONSE]"
                                thinking_active = False # Reset state
                            yield content

                    except json.JSONDecodeError:
                        continue

# --- ANTHROPIC PROVIDER (New) ---
class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20240620"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def stream_chat(self, messages: list) -> AsyncGenerator[str, None]:
        # 1. Extract the system prompt from the first message if it exists
        system_prompt = ""
        user_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_prompt = msg['content']
            else:
                user_messages.append(msg)

        # 2. Use the official Anthropic streaming method
        async with self.client.messages.stream(
            max_tokens=1024,
            messages=user_messages,
            system=system_prompt, # System prompt is a separate param here
            model=self.model,
            temperature=0.7
        ) as stream:
            async for text in stream.text_stream:
                # Note: Claude doesn't have a dedicated 'thinking' field like 
                # reasoning models in Ollama, so we just yield the content.
                yield text
                
# --- GEMINI PROVIDER (New) ---
class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-3-flash-preview"):
        genai.configure(api_key=api_key)
        self.model_name = model_name

    async def stream_chat(self, messages: list) -> AsyncGenerator[str, None]:
        # 1. Separate the system prompt from the conversation history
        system_prompt = ""
        gemini_history = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_prompt = msg['content']
            else:
                # IMPORTANT: Gemini uses "model" instead of "assistant"
                role = "model" if msg['role'] == 'assistant' else "user"
                gemini_history.append({"role": role, "parts": [msg['content']]})

        # 2. Initialize the model with the system instruction
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt
        )

        # 3. Start a chat session and stream the response
        chat = model.start_chat(history=gemini_history[:-1]) # Pass all but the last message
        last_message = gemini_history[-1]["parts"][0] # The current user prompt
        
        response = chat.send_message(last_message, stream=True)
        
        for chunk in response:
            # Gemini yields chunks that contain a 'text' property
            if chunk.text:
                yield chunk.text