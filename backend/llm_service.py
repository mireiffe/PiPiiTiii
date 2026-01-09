"""
LLM Service for PPT Summary Generation
Supports: OpenAI, Google Gemini, OpenAI-compatible APIs
"""

import os
import base64
from typing import AsyncGenerator, List, Dict, Any
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TRUST_ENV = os.environ.get("TRUST_ENV", True).lower() == "true"

class LLMService:
    def __init__(self, config: Dict[str, Any]):
        self.api_type = config.get("api_type", "openai")
        self.api_endpoint = config.get("api_endpoint", "https://api.openai.com/v1")
        self.model_name = config.get("model_name", "gpt-4o")
        self.api_key = os.getenv("LLM_API_KEY")

    def _encode_image_to_base64(self, image_path: str) -> str:
        """Read image file and encode to base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_image_mime_type(self, image_path: str) -> str:
        """Get MIME type from file extension"""
        ext = os.path.splitext(image_path)[1].lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_types.get(ext, "image/png")

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: List[str],
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from LLM with vision support.

        Args:
            system_prompt: System instructions for the LLM
            user_prompt: User query/prompt
            image_paths: List of absolute paths to thumbnail images (max 3)

        Yields:
            Text chunks from the LLM response
        """
        if self.api_type == "openai":
            async for chunk in self._generate_openai_stream(
                system_prompt, user_prompt, image_paths
            ):
                yield chunk
        elif self.api_type == "gemini":
            async for chunk in self._generate_gemini_stream(
                system_prompt, user_prompt, image_paths
            ):
                yield chunk
        elif self.api_type == "openai_compatible":
            async for chunk in self._generate_openai_compatible_stream(
                system_prompt, user_prompt, image_paths
            ):
                yield chunk
        else:
            yield f"Error: Unsupported API type: {self.api_type}"

    async def _generate_openai_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: List[str],
    ) -> AsyncGenerator[str, None]:
        """Generate stream using OpenAI SDK"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            # Build content with images
            content = []

            # Add images first
            for img_path in image_paths:
                if os.path.exists(img_path):
                    base64_image = self._encode_image_to_base64(img_path)
                    mime_type = self._get_image_mime_type(img_path)
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            },
                        }
                    )

            # Add text prompt
            content.append({"type": "text", "text": user_prompt})

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ]

            stream = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except ImportError:
            yield "Error: openai package not installed. Run: pip install openai"
        except Exception as e:
            yield f"Error: {str(e)}"

    async def _generate_gemini_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: List[str],
    ) -> AsyncGenerator[str, None]:
        """Generate stream using Google Gemini SDK"""
        try:
            from google import genai
            from google.genai import types
            from PIL import Image

            client = genai.Client(api_key=self.api_key)

            # Build content with images
            content = []

            for img_path in image_paths:
                if os.path.exists(img_path):
                    img = Image.open(img_path)
                    content.append(img)

            content.append(user_prompt)

            response = await client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=content,
                config=types.GenerateContentConfig(system_instruction=system_prompt),
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except ImportError:
            yield "Error: google-genai package not installed. Run: pip install google-genai pillow"
        except Exception as e:
            yield f"Error: {str(e)}"

    async def _generate_openai_compatible_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: List[str],
    ) -> AsyncGenerator[str, None]:
        """Generate stream using raw HTTP requests (OpenAI-compatible API)"""
        try:
            # Build content with images
            content = []

            # Add images first
            for img_path in image_paths:
                if os.path.exists(img_path):
                    base64_image = self._encode_image_to_base64(img_path)
                    mime_type = self._get_image_mime_type(img_path)
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            },
                        }
                    )

            # Add text prompt
            content.append({"type": "text", "text": user_prompt})

            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                "stream": True,
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Ensure endpoint ends with /chat/completions
            endpoint = self.api_endpoint.rstrip("/")
            if not endpoint.endswith("/chat/completions"):
                endpoint = f"{endpoint}/chat/completions"

            async with httpx.AsyncClient(
                timeout=120.0,
                trust_env=TRUST_ENV,
            ) as client:
                async with client.stream(
                    "POST",
                    endpoint,
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield f"Error: API returned {response.status_code}: {error_text.decode()}"
                        return

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                import json

                                chunk = json.loads(data)
                                if "choices" in chunk and chunk["choices"]:
                                    delta = chunk["choices"][0].get("delta", {})
                                    if "content" in delta and delta["content"]:
                                        yield delta["content"]
                            except Exception:
                                continue

        except Exception as e:
            yield f"Error: {str(e)}"

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Generate non-streaming text response from LLM (no vision support needed for this).

        Args:
            system_prompt: System instructions for the LLM
            user_prompt: User query/prompt

        Returns:
            Complete text response
        """
        response_text = ""
        # We can reuse the stream method and accumulate, or implement specific non-stream calls.
        # reusing stream is easier for now to maintain consistency across providers.
        try:
            async for chunk in self.generate_stream(system_prompt, user_prompt, []):
                response_text += chunk
        except Exception as e:
            return f"Error: {str(e)}"

        return response_text
