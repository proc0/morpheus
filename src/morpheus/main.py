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
        # full_response = "" 
        async for token in service.prompt(user_message):
            # full_response += token
            yield token

        # After the LLM finishes, synthesize the audio
        # We strip [THINKING] or [RESPONSE] tokens if your OllamaService yields them
        # clean_text = full_response.replace("[THINKING]", "").replace("[RESPONSE]", "")
        
        # if full_response.strip():
        #     audio_url = await voice_service.synthesize(full_response)
        #     # Send a special signal to the client so it knows where the audio is
        #     yield f"[AUDIO_READY]: {audio_url}"

    return StreamingResponse(event_generator(), media_type="text/plain")

@app.get("/speak-last-message")
async def speak_last_message():
    # Use the GET endpoint pattern if your Piper setup supports query parameters for streaming, 
    # OR use client.stream with POST if Piper's endpoint supports chunked output.
    # Note: Piper's default server streams best when calling the base URL: f"{PIPER_URL}/?text=..."
    
    text = service.get_last_message()
    if text is None: return None
    # piper_stream_url = f"http://localhost:5000/?text={service.get_last_message()}" 
    payload = {"text": service.get_last_message(), "length_scale": 1.2, "noise_scale": 0.8, "noise_w_scale": 0.5}
    async def audio_generator():
        async with httpx.AsyncClient(timeout=None) as client:
            # client.stream opens a persistent connection and streams bytes
            async with client.stream("POST", "http://localhost:5000/synthesize", json=payload) as response:
                if response.status_code == 200:
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        yield chunk

    # Return a StreamingResponse directly to your client browser or frontend app
    return StreamingResponse(audio_generator(), media_type="audio/wav")


# TODO: Using Piper directly from python to avoid a seperate server
# import argparse
# from flask import Flask, request, Response
# from flask_cors import CORS
# from piper import PiperVoice

# app = Flask(__name__)
# CORS(app)  # This allows Option 1 (your JS Audio element) to connect directly!

# # Load your voice model globally so it stays in memory
# # Update these paths to where your .onnx and .json config files live
# MODEL_PATH = "path/to/voice.onnx"
# voice = PiperVoice.load(MODEL_PATH)

# @app.route("/")
# def synthesize():
#     text = request.args.get("text", "")
    
#     def generate():
#         # voice.synthesize_stream yields raw PCM audio bytes natively
#         for audio_bytes in voice.synthesize_stream(text):
#             yield audio_bytes

#     # Return as a chunked stream
#     return Response(generate(), mimetype="audio/wav")

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
