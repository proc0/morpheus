import wave
from piper import PiperVoice, SynthesisConfig

voice = PiperVoice.load("morpheus-medium.onnx")
syn_config = SynthesisConfig(
    volume=0.5,  # half as loud
    length_scale=1.5,  # twice as slow
    noise_scale=1.0,  # more audio variation
    noise_w_scale=1.0,  # more speaking variation
    normalize_audio=False, # use raw audio from voice
)
with wave.open("test1.wav", "wb") as wav_file:
    # Pre-set the standard Piper parameters (16-bit mono PCM)
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)  # 2 bytes = 16 bit
    wav_file.setframerate(voice.config.sample_rate)
        
    voice.synthesize_wav("Welcome to the world of speech synthesis!", wav_file, syn_config=syn_config)
    # voice.synthesize_wav("Hello this is Morpheus speaking.", wav_file)

# For streaming, use PiperVoice.synthesize:

# for chunk in voice.synthesize("..."):
#     set_audio_format(chunk.sample_rate, chunk.sample_width, chunk.sample_channels)
#     write_raw_data(chunk.audio_int16_bytes)
