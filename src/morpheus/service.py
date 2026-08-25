import os
import time
import httpx
import json
from abc import ABC, abstractmethod
from typing import AsyncGenerator
import uuid
import anthropic
from google import genai
from google.genai import types

from provider import Provider, Configuration, DEFAULT_PROVIDER
from instructions import MORPHEUS_INSTRUCTIONS

class ProviderService(ABC):
    def __init__(self, config: Configuration):
        self.config = config
    
    @abstractmethod
    def get_last_message(self) -> str:
        pass

    @abstractmethod
    def prompt(self, text: str) -> AsyncGenerator[str, None]:
        pass

class OllamaService(ProviderService):
    history = [{ "role": "user", "content": MORPHEUS_INSTRUCTIONS }]

    def get_last_message(self) -> str:
        return self.history[-1]['content'] if len(self.history) > 1 else None

    async def prompt(self, text: str) -> AsyncGenerator[str, None]:
        self.history.append({ "role":"user", "content": text })

        payload = {
            "model": self.config.model,
            "messages": self.history,
            "stream": True,
            "think": False,
            "options": { 
                "temperature": 0.7, 
                "num_predict": 24000
            }
        }

        self.history.append({ "role":"assistant", "content": "" })

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", self.config.url, json=payload) as response:
                async for line in response.aiter_lines():
                    if not line: continue
                    try:
                        chunk = json.loads(line)

                        message = chunk.get("message", {})
                        # thought = message.get("thinking", "")
                        content = message.get("content", "")

                        if chunk['done']:
                            print("[MORPHEUS]")
                            print(self.history[-1]['content'])
                            print(chunk)
                        # if thought and not thinking:
                        #     thinking = True
                        #     yield "[THINKING]"

                        if content:
                            self.history[-1]['content'] = f"{self.history[-1]['content']}{content}"
                            yield content

                            # if thinking:
                            #     thinking = False
                            #     yield f"[RESPONSE] {content}"
                            # else:
                            #     yield content

                    except json.JSONDecodeError:
                        continue

# class AnthropicService(ProviderService):
#     def __init__(self, config: Configuration):
#         super().__init__(config)
#         self.client = anthropic.AsyncAnthropic(api_key=self.config.api_key)

#     async def prompt(self, messages: list) -> AsyncGenerator[str, None]:
#         system_prompt = ""
#         user_messages = []
        
#         for msg in messages:
#             if msg['role'] == 'system':
#                 system_prompt = text
#             else:
#                 user_messages.append(msg)

#         async with self.client.messages.stream(
#             max_tokens=1024,
#             messages=user_messages,
#             system=system_prompt,
#             model=self.config.model,
#             temperature=0.7
#         ) as stream:
#             async for text in stream.text_stream:
#                 yield text
                
class GeminiService(ProviderService):
    def __init__(self, config: Configuration):
        super().__init__(config)
        self.client = genai.Client()
        self.history = []

    def get_last_message(self) -> str:
        return self.history[-1]['parts'][-1]['text']

    async def prompt(self, text: str) -> AsyncGenerator[str, None]:
        system_prompt = ""

        chat = self.client.chats.create(
            model=self.config.model,
            history=self.history,
            config=types.GenerateContentConfig(
                system_instruction=MORPHEUS_INSTRUCTIONS
            )
        )

        response_stream = chat.send_message_stream(text)
        self.history.append(types.Content(role="user", parts=[types.Part(text=text)]))

        full_response = ""
        for chunk in response_stream:
            if chunk.text:
                full_response += chunk.text
                yield chunk.text

        self.history.append(types.Content(role="model", parts=[types.Part(text=full_response)]))


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

    async def synthesize(self, text: str) -> str:
        # Create a unique filename for every single response
        filename = f"response_{uuid.uuid4().hex}.wav" 
        output_path = os.path.join(self.output_dir, filename)

        payload = {"text": text, "length_scale": 1.2, "noise_scale": 0.8, "noise_w_scale": 0.5}
        async with httpx.AsyncClient(timeout=None) as client:
            try:
                response = await client.post(f"{self.piper_url}/synthesize", json=payload)
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    return f"/static/audio/{filename}" # Return the unique name
            except httpx.RequestError as e:
                print(f"Connection error to Piper: {e}")
        return ""

    def cleanup_old_files(self):
        now = time.time()
        for f in os.listdir(self.output_dir):
            f_path = os.path.join(self.output_dir, f)
            # If file is older than 3600 seconds (1 hour), delete it
            if os.stat(f_path).st_mtime < now - 3600:
                os.remove(f_path)