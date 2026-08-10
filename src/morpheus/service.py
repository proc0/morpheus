import os
import httpx
import json
from abc import ABC, abstractmethod
from typing import AsyncGenerator

import anthropic
from google import genai
from google.genai import types

from provider import Provider, Configuration, DEFAULT_PROVIDER
from instructions import MORPHEUS_INSTRUCTIONS

class ProviderService(ABC):
    def __init__(self, config: Configuration):
        self.config = config

    @abstractmethod
    def prompt(self, messages: list) -> AsyncGenerator[str, None]:
        pass

class OllamaService(ProviderService):
    history = [{ "role": "system", "content": MORPHEUS_INSTRUCTIONS }]

    async def prompt(self, messages: list) -> AsyncGenerator[str, None]:
        self.history.append(messages[0])

        payload = {
            "model": self.config.model,
            "messages": self.history,
            "stream": True,
            "options": { 
                "temperature": 0.7, 
                "num_predict": 1024
            }
        }

        self.history.append({ "role":"assistant", "content": "" })
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
                            thinking = True
                            yield "[THINKING]"

                        if content:
                            self.history[-1]['content'] = f"{self.history[-1]['content']}{content}"
                            if thinking:
                                thinking = False
                                yield f"[RESPONSE] {content}"
                            else:
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
        self.history = []

    async def prompt(self, messages: list) -> AsyncGenerator[str, None]:
        system_prompt = ""
        
        msg = messages[0]
        print(msg)
        # for msg in messages:
        #     if msg['role'] == 'system':
        #         system_prompt = msg['content']
        #     else:
        #         # IMPORTANT: Gemini uses "model" instead of "assistant"
        #         role = "model" if msg['role'] == 'assistant' else "user"
        #         self.history.append(types.Content(role=role, parts=[types.Part(part=msg['content'])]))

        config = types.GenerateContentConfig(
            system_instruction=MORPHEUS_INSTRUCTIONS
        )

        chat = self.client.chats.create(
            model=self.config.model,
            history=self.history,
            config=config
        )

        # last_message = self.history[-1]["parts"][0]

        response_stream = chat.send_message_stream(msg['content'])
        self.history.append(types.Content(role="user", parts=[types.Part(text=msg['content'])]))

        full_response = ""
        for chunk in response_stream:
            if chunk.text:
                full_response += chunk.text
                yield chunk.text

        self.history.append(types.Content(role="model", parts=[types.Part(text=full_response)]))
        print(self.history)


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

class VoiceService:
    def __init__(self, piper_url: str = "http://localhost:5000", output_dir: str = "src/morpheus/static/audio"):
        self.piper_url = piper_url
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    async def synthesize(self, text: str, filename: str = "response.wav") -> str:
        """
        Sends text to the Piper HTTP server and saves the resulting WAV file.
        """
        output_path = os.path.join(self.output_dir, filename)
        
        payload = {"text": text}

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.piper_url}/synthesize", json=payload)
            
            if response.status_code == 200:
                # Save the binary content (the .wav file) to disk
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                return f"/static/audio/{filename}"
            else:
                print(f"Piper Server Error: {response.status_code} - {response.text}")
                return ""
