"""
YouTube Transcript Agent
Extracts transcripts from YouTube videos using youtube-transcript-api
"""
import asyncio
import logging
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeAgent:
    """Agent for extracting YouTube video transcripts"""
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extract video ID from YouTube URL
        
        Args:
            url: YouTube URL (various formats supported)
            
        Returns:
            Video ID or None if not found
        """
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        logger.error(f"Could not extract video ID from URL: {url}")
        return None
    
    async def fetch_transcript(self, url: str, languages: list = ['en']) -> Optional[str]:
        """
        Fetch transcript from YouTube video
        
        Args:
            url: YouTube video URL
            languages: List of language codes to try (default: ['en'])
            
        Returns:
            Transcript text or None if failed
        """
        video_id = self.extract_video_id(url)
        if not video_id:
            return None
        
        try:
            # Run in thread pool since youtube-transcript-api is synchronous
            loop = asyncio.get_event_loop()
            transcript_list = await loop.run_in_executor(
                None,
                YouTubeTranscriptApi.get_transcript,
                video_id,
                languages
            )
            
            # Combine all transcript segments
            transcript_text = " ".join([entry['text'] for entry in transcript_list])
            
            logger.info(f"Successfully fetched transcript for video: {video_id}")
            return transcript_text
            
        except TranscriptsDisabled:
            logger.error(f"Transcripts are disabled for video: {video_id}")
            return None
        except NoTranscriptFound:
            logger.error(f"No transcript found for video: {video_id} in languages: {languages}")
            return None
        except Exception as e:
            logger.error(f"Error fetching transcript for video {video_id}: {str(e)}")
            return None
    
    async def fetch_transcript_with_fallback(self, url: str) -> Optional[str]:
        """
        Fetch transcript with language fallback
        
        Args:
            url: YouTube video URL
            
        Returns:
            Transcript text or None if failed
        """
        # Try English first, then common languages
        language_attempts = [
            ['en'],           # English
            ['en-US'],        # English (US)
            ['en-GB'],        # English (UK)
            ['es', 'en'],     # Spanish, English
            ['fr', 'en'],     # French, English
            ['de', 'en'],     # German, English
        ]
        
        for languages in language_attempts:
            transcript = await self.fetch_transcript(url, languages)
            if transcript:
                return transcript
        
        logger.error(f"Failed to fetch transcript for {url} in any language")
        return None


# Tool function for LangChain integration
async def get_youtube_transcript(url: str) -> dict:
    """
    LangChain tool to fetch YouTube transcript
    
    Args:
        url: YouTube video URL
        
    Returns:
        Dictionary with status and transcript/error
    """
    agent = YouTubeAgent()
    transcript = await agent.fetch_transcript_with_fallback(url)
    
    if transcript:
        return {
            "status": "success",
            "transcript": transcript,
            "length": len(transcript)
        }
    else:
        return {
            "status": "error",
            "error": "Failed to fetch transcript"
        }
