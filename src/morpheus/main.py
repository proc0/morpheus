import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from provider import Provider
from service import Service, VoiceService

# run piper server on a different session
# uv run -m piper.http_server -m assets/morpheus-medium.onnx --data-dir assets

app = FastAPI(title="Morpheus API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

service = Service.create(Provider.OLLAMA)
voice_service = VoiceService(piper_url="http://localhost:5000")

# --- ENDPOINTS ---
app.mount("/static", StaticFiles(directory="src/morpheus/static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('src/morpheus/static/index.html')

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("prompt", str)
    
    async def event_generator():
        full_response = "" 
        async for token in service.prompt(user_message):
            full_response += token
            yield token

        # After the LLM finishes, synthesize the audio
        # We strip [THINKING] or [RESPONSE] tokens if your OllamaService yields them
        clean_text = full_response.replace("[THINKING]", "").replace("[RESPONSE]", "")
        
        if clean_text.strip():
            audio_url = await voice_service.synthesize(clean_text)
            # Send a special signal to the client so it knows where the audio is
            yield f"[AUDIO_READY]: {audio_url}"

    return StreamingResponse(event_generator(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
