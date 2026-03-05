"""
YouTube Transcript Agent
Extracts transcripts from YouTube videos.

Primary  : youtube-transcript-api
Fallback : YouTube MCP server (@kimtaeyoon83/mcp-server-youtube-transcript via stdio subprocess)
"""
import asyncio
import logging
import re
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

from .config import MIN_TRANSCRIPT_LENGTH

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

    def _make_api(self) -> YouTubeTranscriptApi:
        """Return a YouTubeTranscriptApi instance (v1.x instance-based API)."""
        return YouTubeTranscriptApi()

    async def fetch_transcript(self, url: str, languages: list = None) -> Optional[str]:
        """Fetch transcript from YouTube using youtube-transcript-api v1.x."""
        if languages is None:
            languages = ["en"]
        video_id = self.extract_video_id(url)
        if not video_id:
            return None
        try:
            api = self._make_api()
            loop = asyncio.get_event_loop()
            fetched = await loop.run_in_executor(
                None, lambda: api.fetch(video_id, languages=languages)
            )
            text = " ".join(snippet.text for snippet in fetched)
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
        """Try multiple languages, then any available transcript."""
        video_id = self.extract_video_id(url)
        if not video_id:
            return None

        # Try preferred languages first
        for languages in [["en"], ["en-US"], ["en-GB"]]:
            transcript = await self.fetch_transcript(url, languages)
            if transcript:
                return transcript

        # Try listing all available transcripts and take the first one
        try:
            api = self._make_api()
            loop = asyncio.get_event_loop()
            transcript_list = await loop.run_in_executor(None, lambda: api.list(video_id))
            for t in transcript_list:
                fetched = await loop.run_in_executor(None, t.fetch)
                text = " ".join(snippet.text for snippet in fetched)
                if text:
                    logger.info("Fetched transcript (any language) for video %s", video_id)
                    return text
        except Exception as exc:
            logger.warning("Could not list transcripts for %s: %s", video_id, exc)

        logger.warning("API transcript fetch exhausted all options for %s", url)
        return None

    # ------------------------------------------------------------------
    # Fallback: YouTube MCP server
    # ------------------------------------------------------------------

    async def fetch_transcript_via_mcp(self, video_id: str) -> Optional[str]:
        """
        Spawn the @kimtaeyoon83/mcp-server-youtube-transcript binary as a
        subprocess and communicate via JSON-RPC over stdio.
        """
        import json
        import asyncio

        # Locate the globally-installed binary
        mcp_bin = "mcp-server-youtube-transcript"

        async def _run() -> Optional[str]:
            proc = None
            try:
                proc = await asyncio.create_subprocess_exec(
                    mcp_bin,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                async def send(msg: dict) -> None:
                    line = json.dumps(msg) + "\n"
                    proc.stdin.write(line.encode())
                    await proc.stdin.drain()

                async def recv_id(target_id: int, timeout: float = 20.0) -> Optional[dict]:
                    """Read stdout lines until we find a response with the given id."""
                    deadline = asyncio.get_event_loop().time() + timeout
                    while asyncio.get_event_loop().time() < deadline:
                        remaining = deadline - asyncio.get_event_loop().time()
                        try:
                            line = await asyncio.wait_for(
                                proc.stdout.readline(), timeout=remaining
                            )
                        except asyncio.TimeoutError:
                            break
                        if not line:
                            break
                        try:
                            msg = json.loads(line.decode().strip())
                            if msg.get("id") == target_id:
                                return msg
                        except json.JSONDecodeError:
                            continue
                    return None

                # 1. Initialize handshake
                await send({
                    "jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "studyvault", "version": "1.0"},
                    },
                })
                init_resp = await recv_id(1, timeout=10.0)
                if init_resp is None:
                    logger.warning("MCP: no initialize response for video %s", video_id)
                    return None

                # 2. Notify initialized
                await send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

                # 3. Call get_transcript tool
                await send({
                    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {
                        "name": "get_transcript",
                        "arguments": {"url": video_id, "lang": "en"},
                    },
                })
                call_resp = await recv_id(2, timeout=30.0)
                if call_resp is None:
                    logger.warning("MCP: no tools/call response for video %s", video_id)
                    return None

                # 4. Extract text from content array
                content = call_resp.get("result", {}).get("content", [])
                parts = [
                    c.get("text", "") for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                ]
                text = " ".join(p for p in parts if p).strip()

                if text:
                    logger.info(
                        "Fetched transcript via MCP for video %s (%d chars)",
                        video_id, len(text),
                    )
                    return text

                # Check for error
                error = call_resp.get("error") or call_resp.get("result", {}).get("error")
                logger.warning("MCP returned no usable text for video %s: %s", video_id, error)
                return None

            except FileNotFoundError:
                logger.error(
                    "MCP binary '%s' not found — Node.js or package not installed", mcp_bin
                )
                return None
            except Exception as exc:
                logger.error("MCP transcript fetch failed for video %s: %s", video_id, exc)
                return None
            finally:
                if proc and proc.returncode is None:
                    try:
                        proc.kill()
                        await proc.wait()
                    except Exception:
                        pass

        return await _run()

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
