"""Voice interaction service for AI coaches using multiple providers."""

import asyncio
import base64
import io
import json
import wave
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import httpx
import numpy as np
from core.cache import get_redis_client
from core.logging import get_logger
from pydantic import BaseModel, Field

logger = get_logger(__name__)


class VoiceProvider(str, Enum):
    """Supported voice service providers."""

    OPENAI = "openai"
    AZURE = "azure"
    GOOGLE = "google"
    AWS_POLLY = "aws_polly"
    ELEVEN_LABS = "eleven_labs"
    LOCAL_WHISPER = "local_whisper"


class VoiceGender(str, Enum):
    """Voice gender options."""

    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class VoiceStyle(str, Enum):
    """Voice speaking styles."""

    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CALM = "calm"
    ENERGETIC = "energetic"
    EMPATHETIC = "empathetic"
    AUTHORITATIVE = "authoritative"


class AudioFormat(str, Enum):
    """Supported audio formats."""

    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    WEBM = "webm"
    PCM = "pcm"


class VoiceConfig(BaseModel):
    """Voice configuration settings."""

    provider: VoiceProvider = Field(default=VoiceProvider.OPENAI)
    voice_id: Optional[str] = None
    gender: VoiceGender = Field(default=VoiceGender.NEUTRAL)
    style: VoiceStyle = Field(default=VoiceStyle.PROFESSIONAL)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)
    volume: float = Field(default=1.0, ge=0.1, le=1.0)
    language: str = Field(default="en-US")
    emotion_level: float = Field(default=0.5, ge=0.0, le=1.0)
    sample_rate: int = Field(default=24000)
    output_format: AudioFormat = Field(default=AudioFormat.MP3)


class TranscriptionResult(BaseModel):
    """Speech-to-text transcription result."""

    text: str
    confidence: float
    language: str
    duration: float
    words: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VoiceService:
    """Main voice interaction service."""

    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self.api_keys = api_keys or {}
        self.providers = {}
        self.cache = get_redis_client()
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize voice providers based on available API keys."""

        if "openai" in self.api_keys:
            self.providers[VoiceProvider.OPENAI] = OpenAIVoiceProvider(
                self.api_keys["openai"]
            )

        if "azure" in self.api_keys:
            self.providers[VoiceProvider.AZURE] = AzureVoiceProvider(
                self.api_keys["azure"]
            )

        if "eleven_labs" in self.api_keys:
            self.providers[VoiceProvider.ELEVEN_LABS] = ElevenLabsProvider(
                self.api_keys["eleven_labs"]
            )

        # Always add local Whisper if available
        self.providers[VoiceProvider.LOCAL_WHISPER] = LocalWhisperProvider()

    async def transcribe(
        self,
        audio_data: Union[bytes, str],  # bytes or base64 string
        provider: Optional[VoiceProvider] = None,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio to text."""

        # Convert base64 to bytes if needed
        if isinstance(audio_data, str):
            audio_data = base64.b64decode(audio_data)

        # Select provider
        provider = provider or VoiceProvider.OPENAI
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not available")

        # Check cache
        cache_key = self._get_cache_key("stt", audio_data)
        cached = await self._get_cached(cache_key)
        if cached:
            return TranscriptionResult(**cached)

        # Transcribe
        result = await self.providers[provider].transcribe(audio_data, language)

        # Cache result
        await self._cache_result(cache_key, result.dict())

        return result

    async def synthesize(
        self, text: str, config: Optional[VoiceConfig] = None
    ) -> bytes:
        """Synthesize text to speech."""

        config = config or VoiceConfig()

        # Select provider
        if config.provider not in self.providers:
            # Fallback to available provider
            config.provider = next(iter(self.providers.keys()))

        # Check cache
        cache_key = self._get_cache_key("tts", f"{text}:{config.json()}")
        cached = await self._get_cached(cache_key)
        if cached:
            return base64.b64decode(cached["audio"])

        # Synthesize
        audio_data = await self.providers[config.provider].synthesize(text, config)

        # Cache result
        await self._cache_result(
            cache_key, {"audio": base64.b64encode(audio_data).decode()}
        )

        return audio_data

    async def stream_synthesize(
        self, text: str, config: Optional[VoiceConfig] = None
    ) -> AsyncIterator[bytes]:
        """Stream text-to-speech synthesis."""

        config = config or VoiceConfig()

        if config.provider not in self.providers:
            config.provider = next(iter(self.providers.keys()))

        provider = self.providers[config.provider]

        if hasattr(provider, "stream_synthesize"):
            async for chunk in provider.stream_synthesize(text, config):
                yield chunk
        else:
            # Fallback to non-streaming
            audio = await self.synthesize(text, config)
            # Chunk the audio for streaming effect
            chunk_size = 4096
            for i in range(0, len(audio), chunk_size):
                yield audio[i : i + chunk_size]

    async def create_coach_voice(
        self, coach_id: str, name: str, description: str, config: VoiceConfig
    ) -> Dict[str, Any]:
        """Create a custom voice profile for a coach."""

        voice_profile = {
            "id": f"voice_{coach_id}",
            "coach_id": coach_id,
            "name": name,
            "description": description,
            "config": config.dict(),
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store in cache/database
        await self._cache_result(f"voice_profile:{coach_id}", voice_profile)

        return voice_profile

    async def get_coach_voice(self, coach_id: str) -> Optional[Dict[str, Any]]:
        """Get voice profile for a coach."""
        return await self._get_cached(f"voice_profile:{coach_id}")

    def _get_cache_key(self, prefix: str, data: Union[str, bytes]) -> str:
        """Generate cache key."""
        import hashlib

        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="ignore")

        hash_val = hashlib.md5(data.encode()).hexdigest()
        return f"voice:{prefix}:{hash_val}"

    async def _get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached result."""
        try:
            data = await self.cache.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def _cache_result(self, key: str, data: Dict[str, Any]):
        """Cache result with TTL."""
        try:
            await self.cache.setex(key, 3600, json.dumps(data))
        except Exception as e:
            logger.error(f"Cache set error: {e}")


class OpenAIVoiceProvider:
    """OpenAI Whisper and TTS provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"}, timeout=60
        )

    async def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe using Whisper API."""

        files = {
            "file": ("audio.wav", audio_data, "audio/wav"),
            "model": (None, "whisper-1"),
        }

        if language:
            files["language"] = (None, language)

        response = await self.client.post(
            f"{self.base_url}/audio/transcriptions", files=files
        )
        response.raise_for_status()

        data = response.json()
        return TranscriptionResult(
            text=data["text"],
            confidence=0.95,  # OpenAI doesn't provide confidence
            language=language or "en",
            duration=0.0,  # Not provided
            metadata=data,
        )

    async def synthesize(self, text: str, config: VoiceConfig) -> bytes:
        """Synthesize using OpenAI TTS."""

        # Map voice configuration to OpenAI voices
        voice_map = {
            (VoiceGender.MALE, VoiceStyle.PROFESSIONAL): "echo",
            (VoiceGender.MALE, VoiceStyle.FRIENDLY): "onyx",
            (VoiceGender.FEMALE, VoiceStyle.PROFESSIONAL): "nova",
            (VoiceGender.FEMALE, VoiceStyle.FRIENDLY): "shimmer",
            (VoiceGender.NEUTRAL, VoiceStyle.PROFESSIONAL): "alloy",
            (VoiceGender.NEUTRAL, VoiceStyle.CALM): "fable",
        }

        voice = voice_map.get((config.gender, config.style), "alloy")  # Default

        response = await self.client.post(
            f"{self.base_url}/audio/speech",
            json={
                "model": "tts-1-hd",  # High quality
                "input": text,
                "voice": voice,
                "speed": config.speed,
            },
        )
        response.raise_for_status()

        return response.content

    async def stream_synthesize(
        self, text: str, config: VoiceConfig
    ) -> AsyncIterator[bytes]:
        """Stream TTS synthesis."""

        voice_map = {
            (VoiceGender.MALE, VoiceStyle.PROFESSIONAL): "echo",
            (VoiceGender.FEMALE, VoiceStyle.PROFESSIONAL): "nova",
            (VoiceGender.NEUTRAL, VoiceStyle.PROFESSIONAL): "alloy",
        }

        voice = voice_map.get((config.gender, config.style), "alloy")

        async with self.client.stream(
            "POST",
            f"{self.base_url}/audio/speech",
            json={
                "model": "tts-1",  # Faster model for streaming
                "input": text,
                "voice": voice,
                "speed": config.speed,
                "response_format": config.output_format.value,
            },
        ) as response:
            async for chunk in response.aiter_bytes(chunk_size=1024):
                yield chunk


class LocalWhisperProvider:
    """Local Whisper model for privacy-conscious users."""

    def __init__(self):
        self.model = None
        self.model_loaded = False

    async def _load_model(self):
        """Load Whisper model lazily."""
        if not self.model_loaded:
            try:
                import whisper

                self.model = whisper.load_model("base")
                self.model_loaded = True
            except ImportError:
                logger.error("Whisper not installed. Run: pip install openai-whisper")
                raise

    async def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe using local Whisper."""

        await self._load_model()

        # Save audio to temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            audio_file = f.name

        try:
            # Transcribe
            result = self.model.transcribe(audio_file, language=language)

            return TranscriptionResult(
                text=result["text"],
                confidence=0.9,
                language=result.get("language", language or "en"),
                duration=0.0,
                metadata=result,
            )
        finally:
            import os

            os.unlink(audio_file)

    async def synthesize(self, text: str, config: VoiceConfig) -> bytes:
        """Local TTS not implemented - would need additional library."""
        raise NotImplementedError("Local TTS requires additional setup")


class AzureVoiceProvider:
    """Azure Cognitive Services Speech provider."""

    def __init__(self, api_key: str, region: str = "eastus"):
        self.api_key = api_key
        self.region = region
        self.base_url = f"https://{region}.api.cognitive.microsoft.com"
        self.client = httpx.AsyncClient(
            headers={"Ocp-Apim-Subscription-Key": api_key}, timeout=60
        )

    async def transcribe(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """Transcribe using Azure Speech Services."""

        url = f"{self.base_url}/speechtotext/v3.0/transcriptions"

        response = await self.client.post(
            url,
            content=audio_data,
            headers={"Content-Type": "audio/wav", "Accept": "application/json"},
        )
        response.raise_for_status()

        data = response.json()
        return TranscriptionResult(
            text=data["DisplayText"],
            confidence=data.get("NBest", [{}])[0].get("Confidence", 0.9),
            language=language or "en-US",
            duration=data.get("Duration", 0.0),
            metadata=data,
        )

    async def synthesize(self, text: str, config: VoiceConfig) -> bytes:
        """Synthesize using Azure Neural TTS."""

        # Map configuration to Azure voices
        voice_map = {
            (VoiceGender.MALE, "en-US"): "en-US-JennyNeural",
            (VoiceGender.FEMALE, "en-US"): "en-US-AriaNeural",
            (VoiceGender.NEUTRAL, "en-US"): "en-US-GuyNeural",
        }

        voice = config.voice_id or voice_map.get(
            (config.gender, config.language), "en-US-JennyNeural"
        )

        # Create SSML
        ssml = f"""
        <speak version='1.0' xml:lang='{config.language}'>
            <voice xml:lang='{config.language}' name='{voice}'>
                <prosody rate='{config.speed}' pitch='{config.pitch}'>
                    {text}
                </prosody>
            </voice>
        </speak>
        """

        response = await self.client.post(
            f"{self.base_url}/cognitiveservices/v1",
            content=ssml,
            headers={
                "X-Microsoft-OutputFormat": f"audio-24khz-160kbitrate-mono-{config.output_format.value}",
                "Content-Type": "application/ssml+xml",
            },
        )
        response.raise_for_status()

        return response.content


class ElevenLabsProvider:
    """ElevenLabs high-quality voice synthesis."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.client = httpx.AsyncClient(headers={"xi-api-key": api_key}, timeout=60)

    async def synthesize(self, text: str, config: VoiceConfig) -> bytes:
        """Synthesize using ElevenLabs."""

        # Use provided voice ID or default
        voice_id = config.voice_id or "21m00Tcm4TlvDq8ikWAM"  # Default voice

        response = await self.client.post(
            f"{self.base_url}/text-to-speech/{voice_id}",
            json={
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": config.emotion_level,
                    "use_speaker_boost": True,
                },
            },
        )
        response.raise_for_status()

        return response.content

    async def stream_synthesize(
        self, text: str, config: VoiceConfig
    ) -> AsyncIterator[bytes]:
        """Stream synthesis from ElevenLabs."""

        voice_id = config.voice_id or "21m00Tcm4TlvDq8ikWAM"

        async with self.client.stream(
            "POST",
            f"{self.base_url}/text-to-speech/{voice_id}/stream",
            json={
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
        ) as response:
            async for chunk in response.aiter_bytes(chunk_size=1024):
                yield chunk
