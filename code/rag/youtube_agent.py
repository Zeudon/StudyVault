"""
YouTube Transcript Agent
Extracts transcripts from YouTube videos.

Primary  : youtube-transcript-api
Fallback : YouTube MCP server (httpx HTTP call when transcript is too short or unavailable)
"""
import asyncio
import logging
import re
from typing import Optional

import httpx
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

from .config import MIN_TRANSCRIPT_LENGTH, YOUTUBE_MCP_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeAgent:
    """Agent for extracting YouTube video transcripts."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Return the 11-char video ID from a YouTube URL, or None."""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        logger.error("Could not extract video ID from URL: %s", url)
        return None

    @staticmethod
    def is_transcript_sufficient(transcript: Optional[str]) -> bool:
        """Return True when *transcript* has enough content to be useful."""
        return bool(transcript and len(transcript.strip()) >= MIN_TRANSCRIPT_LENGTH)

    # ------------------------------------------------------------------
    # Primary: youtube-transcript-api
    # ------------------------------------------------------------------

    async def fetch_transcript(self, url: str, languages: list = None) -> Optional[str]:
        """Fetch transcript from YouTube using youtube-transcript-api."""
        if languages is None:
            languages = ["en"]
        video_id = self.extract_video_id(url)
        if not video_id:
            return None
        try:
            loop = asyncio.get_event_loop()
            entries = await loop.run_in_executor(
                None, YouTubeTranscriptApi.get_transcript, video_id, languages
            )
            text = " ".join(e["text"] for e in entries)
            logger.info("Fetched transcript via API for video %s (%d chars)", video_id, len(text))
            return text
        except TranscriptsDisabled:
            logger.warning("Transcripts disabled for video: %s", video_id)
            return None
        except NoTranscriptFound:
            logger.warning("No transcript found for video %s in %s", video_id, languages)
            return None
        except Exception as exc:
            logger.error("Error fetching transcript for %s: %s", video_id, exc)
            return None

    async def fetch_transcript_with_fallback(self, url: str) -> Optional[str]:
        """Try multiple languages via youtube-transcript-api."""
        language_attempts = [
            ["en"], ["en-US"], ["en-GB"],
            ["es", "en"], ["fr", "en"], ["de", "en"],
        ]
        for languages in language_attempts:
            transcript = await self.fetch_transcript(url, languages)
            if transcript:
                return transcript
        logger.warning("API transcript fetch exhausted all languages for %s", url)
        return None

    # ------------------------------------------------------------------
    # Fallback: YouTube MCP server
    # ------------------------------------------------------------------

    async def fetch_transcript_via_mcp(self, video_id: str) -> Optional[str]:
        """
        Call the YouTube MCP server to obtain a transcript.
        Expected MCP endpoint: POST {YOUTUBE_MCP_URL}/transcript
        Body: {"video_id": "<id>"}
        Response: {"transcript": "<text>"} or {"error": "<msg>"}
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{YOUTUBE_MCP_URL}/transcript",
                    json={"video_id": video_id},
                )
                resp.raise_for_status()
                data = resp.json()
                transcript = data.get("transcript", "")
                if transcript:
                    logger.info(
                        "Fetched transcript via MCP for video %s (%d chars)",
                        video_id, len(transcript),
                    )
                    return transcript
                logger.warning("MCP returned empty transcript for video %s", video_id)
                return None
        except Exception as exc:
            logger.error("MCP transcript fetch failed for video %s: %s", video_id, exc)
            return None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def get_transcript(self, url: str) -> str:
        """
        Return a transcript string for *url*.

        1. Try youtube-transcript-api (multiple language fallbacks).
        2. If result is absent or insufficient, try YouTube MCP server.
        3. Raise ValueError if both strategies fail.
        """
        transcript = await self.fetch_transcript_with_fallback(url)

        if not self.is_transcript_sufficient(transcript):
            logger.info("API transcript insufficient — trying MCP server for %s", url)
            video_id = self.extract_video_id(url)
            if video_id:
                transcript = await self.fetch_transcript_via_mcp(video_id)

        if not self.is_transcript_sufficient(transcript):
            raise ValueError(
                f"Could not obtain a usable transcript for {url}. "
                "The video may have transcripts disabled or unavailable."
            )

        return transcript.strip()

# ---------------------------------------------------------------------------
# Standalone async helper (kept for backward compatibility / tools.py)
# ---------------------------------------------------------------------------

async def get_youtube_transcript(url: str) -> dict:
    """Fetch a YouTube transcript and return a status dict."""
    agent = YouTubeAgent()
    try:
        transcript = await agent.get_transcript(url)
        return {"status": "success", "transcript": transcript, "length": len(transcript)}
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
