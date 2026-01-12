"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Union


@dataclass
class ImageContent:
    """Image content for multimodal messages."""

    url: str  # Can be a URL or base64 data URL (data:image/jpeg;base64,...)
    detail: str = "auto"  # "auto", "low", "high" (for OpenAI)


@dataclass
class TextContent:
    """Text content for multimodal messages."""

    text: str


@dataclass
class MessageContent:
    """Content block in a multimodal message."""

    type: str  # "text" or "image_url"
    text: Optional[str] = None
    image_url: Optional[ImageContent] = None

    @classmethod
    def from_text(cls, text: str) -> "MessageContent":
        """Create a text content block."""
        return cls(type="text", text=text)

    @classmethod
    def from_image(cls, url: str, detail: str = "auto") -> "MessageContent":
        """Create an image content block."""
        return cls(type="image_url", image_url=ImageContent(url=url, detail=detail))


@dataclass
class Message:
    """Chat message supporting both text-only and multimodal content."""

    role: str  # "system", "user", "assistant"
    content: Union[str, List[MessageContent]] = ""

    def is_multimodal(self) -> bool:
        """Check if this message contains multimodal content."""
        return isinstance(self.content, list)

    def get_text_content(self) -> str:
        """Get the text content of the message."""
        if isinstance(self.content, str):
            return self.content
        # Extract text from multimodal content
        texts = []
        for part in self.content:
            if part.type == "text" and part.text:
                texts.append(part.text)
        return "\n".join(texts)

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI API format."""
        if isinstance(self.content, str):
            return {"role": self.role, "content": self.content}

        # Multimodal format
        content_parts = []
        for part in self.content:
            if part.type == "text":
                content_parts.append({"type": "text", "text": part.text})
            elif part.type == "image_url" and part.image_url:
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": part.image_url.url,
                            "detail": part.image_url.detail,
                        },
                    }
                )

        return {"role": self.role, "content": content_parts}

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert to Anthropic API format."""
        if isinstance(self.content, str):
            return {"role": self.role, "content": self.content}

        # Anthropic multimodal format
        content_parts = []
        for part in self.content:
            if part.type == "text":
                content_parts.append({"type": "text", "text": part.text})
            elif part.type == "image_url" and part.image_url:
                url = part.image_url.url
                # Anthropic requires base64 format
                if url.startswith("data:"):
                    # Parse data URL: data:image/jpeg;base64,xxxxx
                    try:
                        header, data = url.split(",", 1)
                        media_type = header.split(";")[0].split(":")[1]
                        content_parts.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": data,
                                },
                            }
                        )
                    except (ValueError, IndexError):
                        # Skip invalid data URLs
                        pass
                else:
                    # For regular URLs, Anthropic doesn't support direct URLs
                    # This would need to be fetched and converted to base64
                    pass

        return {"role": self.role, "content": content_parts}


@dataclass
class LLMConfig:
    """LLM configuration."""

    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stream: bool = True


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        config: LLMConfig,
    ) -> str:
        """Send chat request and get complete response."""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Message],
        config: LLMConfig,
    ) -> AsyncIterator[str]:
        """Send chat request and stream response."""
        pass

    @abstractmethod
    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Generate embeddings for text."""
        pass

    @abstractmethod
    async def count_tokens(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> int:
        """Count tokens in text."""
        pass
