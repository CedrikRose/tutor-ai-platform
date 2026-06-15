"""
Reducto API Client

Handles PDF parsing via Reducto API with caching, error handling, and async support.
"""
import asyncio
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional
import aiofiles
import requests

from config import settings
from file_storage import get_storage

logger = logging.getLogger(__name__)


class ReductoAPIError(Exception):
    """Reducto API specific errors."""
    pass


class ReductoClient:
    """Client for Reducto PDF parsing API."""
    
    UPLOAD_ENDPOINT = "https://platform.reducto.ai/upload"
    PARSE_ENDPOINT = "https://platform.reducto.ai/parse"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.reducto_api_key
        self.storage = get_storage()
        self.cache_dir = Path("uploads/.reducto_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, file_path: str) -> Path:
        """Get cache path for a file using MD5 hash."""
        hash_md5 = hashlib.md5(file_path.encode()).hexdigest()
        return self.cache_dir / f"{hash_md5}.json"
    
    def _check_cache(self, file_path: str) -> Optional[Dict]:
        """Check if cached response exists."""
        cache_path = self._get_cache_path(file_path)
        if cache_path.exists():
            logger.info(f"[REDUCTO] Cache HIT: {file_path}")
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache for {file_path}: {e}")
                return None
        return None
    
    def _save_cache(self, file_path: str, response: Dict):
        """Save response to cache."""
        cache_path = self._get_cache_path(file_path)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(response, f, ensure_ascii=False, indent=2)
            logger.info(f"[REDUCTO] Cached response for {file_path}")
        except Exception as e:
            logger.warning(f"Failed to save cache for {file_path}: {e}")
    
    def _upload_file(self, file_path: str) -> str:
        """Upload file to Reducto and return reducto:// URL."""
        logger.info(f"[REDUCTO] Uploading file: {file_path}")
        
        try:
            # Get file content from storage (handles S3 and local)
            file_content = self.storage.get_file(file_path)
            filename = Path(file_path).name
            
            # Upload to Reducto
            headers = {"Authorization": f"Bearer {self.api_key}"}
            files = {"file": (filename, file_content, "application/pdf")}
            
            response = requests.post(
                self.UPLOAD_ENDPOINT,
                headers=headers,
                files=files,
                timeout=60
            )
            
            if response.status_code != 200:
                raise ReductoAPIError(f"Upload failed: {response.status_code} - {response.text}")
            
            upload_data = response.json()
            reducto_url = upload_data.get("file_id") or upload_data.get("url")
            reducto_url = upload_data.get("file_id") or upload_data.get("url")
            reducto_url = upload_data.get("file_id") or upload_data.get("url")
            reducto_url = upload_data.get("file_id") or upload_data.get("url")
            
            logger.info(f"[REDUCTO] Upload successful: {reducto_url}")
            return reducto_url
            
        except Exception as e:
            logger.error(f"[REDUCTO] Upload error: {e}")
            raise ReductoAPIError(f"Failed to upload file: {e}")
    
    def _parse_with_reducto(self, reducto_url: str, attempt: int = 1) -> Dict:
        """Call Reducto parse API."""
        logger.info(f"[REDUCTO] Parsing (attempt {attempt}): {reducto_url}")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "input": reducto_url,
            "retrieval": {
                "chunking": {
                    "chunk_mode": "section",
                    "chunk_size": 1000
                }
            },
            "formatting": {
                "table_output_format": "md",
                "add_page_markers": True
            }
        }
        
        try:
            response = requests.post(
                self.PARSE_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=120
            )
            
            # Handle rate limiting with exponential backoff
            if response.status_code == 429:
                if attempt < 3:
                    wait_time = 2 ** attempt  # 2s, 4s, 8s
                    logger.warning(f"[REDUCTO] Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    return self._parse_with_reducto(reducto_url, attempt + 1)
                else:
                    raise ReductoAPIError(f"Rate limit exceeded after 3 attempts")
            
            if response.status_code == 422:
                error_detail = response.json().get("detail", response.text)
                raise ReductoAPIError(f"Validation error: {error_detail}")
            
            if response.status_code != 200:
                raise ReductoAPIError(f"Parse failed: {response.status_code} - {response.text}")
            
            parse_data = response.json()
            
            # Handle large responses (result.type == "url")
            if parse_data.get("result", {}).get("type") == "url":
                result_url = parse_data["result"]["url"]
                logger.info(f"[REDUCTO] Large response, fetching from: {result_url}")
                
                result_response = requests.get(result_url, timeout=60)
                if result_response.status_code == 200:
                    parse_data["result"] = result_response.json()
                else:
                    raise ReductoAPIError(f"Failed to fetch large result: {result_response.status_code}")
            
            job_id = parse_data.get("job_id")
            duration = parse_data.get("duration", 0)
            num_chunks = len(parse_data.get("result", {}).get("chunks", []))
            
            logger.info(f"[REDUCTO] Parse complete: job_id={job_id}, duration={duration}s, chunks={num_chunks}")
            
            return parse_data
            
        except requests.exceptions.Timeout:
            if attempt < 2:
                logger.warning(f"[REDUCTO] Timeout, retrying...")
                time.sleep(5)
                return self._parse_with_reducto(reducto_url, attempt + 1)
            else:
                raise ReductoAPIError("Parse timeout after 2 attempts")
        
        except Exception as e:
            logger.error(f"[REDUCTO] Parse error: {e}")
            raise ReductoAPIError(f"Parse failed: {e}")
    
    def parse_pdf_sync(self, file_path: str) -> Dict:
        """Parse PDF synchronously with caching."""
        # Check cache first
        cached = self._check_cache(file_path)
        if cached:
            return cached
        
        # Upload and parse
        reducto_url = self._upload_file(file_path)
        parse_result = self._parse_with_reducto(reducto_url)
        
        # Save to cache
        self._save_cache(file_path, parse_result)
        
        return parse_result
    
    async def parse_pdf(self, file_path: str) -> Dict:
        """Parse PDF asynchronously with caching."""
        # Check cache first
        cached = self._check_cache(file_path)
        if cached:
            return cached
        
        # Run sync parse in executor to avoid blocking
        loop = asyncio.get_event_loop()
        parse_result = await loop.run_in_executor(None, self.parse_pdf_sync, file_path)
        
        return parse_result


# Global client instance
_reducto_client: Optional[ReductoClient] = None


def get_reducto_client() -> ReductoClient:
    """Get global Reducto client instance."""
    global _reducto_client
    if _reducto_client is None:
        _reducto_client = ReductoClient()
    return _reducto_client
