"""VLM client for interacting with vision-language models."""

import asyncio
import hashlib
import json
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


class VlmClient:
    """
    Client for interacting with Vision Language Models via Vertex AI.

    Supports text-only and multimodal (text + image/PDF) interactions.
    """

    def __init__(
        self,
        model_name: str | None = None,
        project: str | None = None,
        location: str | None = None,
        max_retries: int = 5,
        base_delay: float = 5.0,
        max_delay: float = 60.0,
        cache_dir: Path | str | None = None,
        enable_cache: bool = True,
    ) -> None:
        """
        Initialize the VLM client.

        Args:
            model_name: Name of the model to use. Defaults to env var.
            project: Google Cloud project ID. Defaults to GCP_PROJECT_ID env.
            location: GCP location. Defaults to GCP_LOCATION env or us-central1.
            max_retries: Maximum number of retries for rate limit errors.
            base_delay: Base delay in seconds for exponential backoff.
            max_delay: Maximum delay in seconds between retries.
            cache_dir: Directory for caching responses. Defaults to .cache/vlm.
            enable_cache: Whether to enable caching. Defaults to True.
        """
        self._model_name = model_name or os.getenv(
            "VERTEX_AI_MODEL_NAME", "gemini-2.0-flash"
        )
        self._project = project or os.getenv("GCP_PROJECT_ID")
        self._location = location or os.getenv("GCP_LOCATION", "us-central1")
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._enable_cache = enable_cache

        # Setup cache directory
        if cache_dir:
            self._cache_dir = Path(cache_dir)
        else:
            self._cache_dir = Path(".cache/vlm")

        if self._enable_cache:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

        if not self._project:
            raise ValueError(
                "GCP_PROJECT_ID must be set in .env or passed as argument"
            )

        # Create client with Vertex AI
        self._client = genai.Client(
            vertexai=True,
            project=self._project,
            location=self._location,
        )

        print(f"[VlmClient] Initialized with Vertex AI")
        print(f"[VlmClient]   Model: {self._model_name}")
        print(f"[VlmClient]   Project: {self._project}")
        print(f"[VlmClient]   Location: {self._location}")
        print(f"[VlmClient]   Cache: {self._enable_cache} ({self._cache_dir})")

    def _get_cache_key(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        file_hashes: list[str] | None = None,
    ) -> str:
        """Generate a cache key from input parameters."""
        key_data = {
            "model": self._model_name,
            "prompt": prompt,
            "system_prompt": system_prompt,
            "temperature": temperature,
            "file_hashes": file_hashes or [],
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _get_file_hash(self, file_path: Path) -> str:
        """Get hash of file."""
        return hashlib.md5(file_path.read_bytes()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> str | None:
        """Get cached response if exists."""
        if not self._enable_cache:
            return None

        cache_file = self._cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                print(f"[CACHE] Hit: {cache_key[:12]}...")
                return data["response"]
            except (json.JSONDecodeError, KeyError):
                return None
        return None

    def _save_to_cache(self, cache_key: str, response: str) -> None:
        """Save response to cache."""
        if not self._enable_cache:
            return

        cache_file = self._cache_dir / f"{cache_key}.json"
        data = {"response": response}
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"[CACHE] Saved: {cache_key[:12]}...")

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if the error is retryable (rate limit or timeout)."""
        if isinstance(error, asyncio.TimeoutError):
            return True
        error_str = str(error).lower()
        return (
            "429" in error_str
            or "resource_exhausted" in error_str
            or "rate" in error_str and "limit" in error_str
            or "quota" in error_str
        )

    async def _generate_with_retry(
        self,
        contents: list,
        config: types.GenerateContentConfig,
        timeout: float = 120.0,
    ) -> str:
        """Generate content with exponential backoff retry for rate limits."""
        last_error = None

        for attempt in range(self._max_retries + 1):
            try:
                print(f"[VLM] Calling API (attempt {attempt + 1})...")
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self._model_name,
                        contents=contents,
                        config=config,
                    ),
                    timeout=timeout,
                )
                print(f"[VLM] API response received")
                return response.text
            except Exception as e:
                last_error = e
                if not self._is_retryable_error(e):
                    raise
                error_type = (
                    "Timeout" if isinstance(e, asyncio.TimeoutError) else "Rate limit"
                )
                print(f"[VLM] {error_type} error: {e}")

                if attempt < self._max_retries:
                    delay = min(
                        self._base_delay * (2 ** attempt) + random.uniform(0, 1),
                        self._max_delay
                    )
                    print(f"[RETRY] Rate limit hit, waiting {delay:.1f}s "
                          f"(attempt {attempt + 1}/{self._max_retries})...")
                    await asyncio.sleep(delay)

        raise last_error

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.5,
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: User prompt.
            system_prompt: Optional system prompt.
            temperature: Model temperature.

        Returns:
            Generated text response.
        """
        # Check cache
        cache_key = self._get_cache_key(prompt, system_prompt, temperature)
        cached = self._get_cached_response(cache_key)
        if cached is not None:
            return cached

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_prompt,
        )

        response = await self._generate_with_retry(
            contents=[prompt],
            config=config,
        )

        # Save to cache
        self._save_to_cache(cache_key, response)

        return response

    async def generate_with_files(
        self,
        prompt: str,
        file_paths: list[Path],
        system_prompt: str | None = None,
        temperature: float = 0.5,
    ) -> str:
        """
        Generate text from a prompt with files (images or PDFs).

        Args:
            prompt: User prompt.
            file_paths: List of file paths (images or PDFs).
            system_prompt: Optional system prompt.
            temperature: Model temperature.

        Returns:
            Generated text response.
        """
        # Calculate file hashes for cache key
        file_hashes = []
        for file_path in file_paths:
            if file_path.exists():
                file_hashes.append(self._get_file_hash(file_path))

        # Check cache
        cache_key = self._get_cache_key(
            prompt, system_prompt, temperature, file_hashes
        )
        cached = self._get_cached_response(cache_key)
        if cached is not None:
            return cached

        contents = []

        # Add files
        for file_path in file_paths:
            if file_path.exists():
                file_bytes = file_path.read_bytes()
                mime_type = self._get_mime_type(file_path)
                contents.append(
                    types.Part.from_bytes(
                        data=file_bytes,
                        mime_type=mime_type,
                    )
                )

        # Add text prompt
        contents.append(prompt)

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_prompt,
        )

        response = await self._generate_with_retry(
            contents=contents,
            config=config,
        )

        # Save to cache
        self._save_to_cache(cache_key, response)

        return response

    async def generate_with_images(
        self,
        prompt: str,
        image_paths: list[Path],
        system_prompt: str | None = None,
        temperature: float = 0.5,
    ) -> str:
        """
        Generate text from a prompt with images.

        This is an alias for generate_with_files for backwards compatibility.

        Args:
            prompt: User prompt.
            image_paths: List of image file paths.
            system_prompt: Optional system prompt.
            temperature: Model temperature.

        Returns:
            Generated text response.
        """
        return await self.generate_with_files(
            prompt=prompt,
            file_paths=image_paths,
            system_prompt=system_prompt,
            temperature=temperature,
        )

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type for file."""
        suffix = file_path.suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".pdf": "application/pdf",
        }
        return mime_types.get(suffix, "application/octet-stream")

    def clear_cache(self) -> int:
        """
        Clear all cached responses.

        Returns:
            Number of cache files deleted.
        """
        count = 0
        if self._cache_dir.exists():
            for cache_file in self._cache_dir.glob("*.json"):
                cache_file.unlink()
                count += 1
        print(f"[CACHE] Cleared {count} cached responses")
        return count
