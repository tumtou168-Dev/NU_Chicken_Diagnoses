# app/services/voice_service.py
import asyncio
import io
import hashlib
import concurrent.futures
import edge_tts

VOICES = {
    "km": "km-KH-SreymomNeural",  # Female Khmer Neural voice
    "en": "en-US-AriaNeural",     # Female English Neural voice
}

_AUDIO_CACHE: dict[str, bytes] = {}


class VoiceService:
    @classmethod
    async def _generate_bytes(cls, text: str, voice: str) -> bytes:
        communicate = edge_tts.Communicate(text, voice)
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
        return buffer.getvalue()

    @classmethod
    def text_to_speech(cls, text: str, lang: str = "km") -> bytes:
        """
        Converts text to speech using Edge TTS neural voices.
        - lang='km': Female Khmer (km-KH-SreymomNeural)
        - lang='en': Female English (en-US-AriaNeural)
        """
        voice = VOICES.get(lang, VOICES["km"])
        cache_key = hashlib.md5(f"{voice}:{text}".encode("utf-8")).hexdigest()
        
        if cache_key in _AUDIO_CACHE:
            return _AUDIO_CACHE[cache_key]

        # Handle event loops gracefully across worker threads
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    audio_bytes = pool.submit(lambda: asyncio.run(cls._generate_bytes(text, voice))).result()
            else:
                audio_bytes = loop.run_until_complete(cls._generate_bytes(text, voice))
        except RuntimeError:
            audio_bytes = asyncio.run(cls._generate_bytes(text, voice))

        if audio_bytes:
            _AUDIO_CACHE[cache_key] = audio_bytes
            
        return audio_bytes
