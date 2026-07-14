# ALONE-CODER
"""
SaaS YouTube backend downloader (youtube-api-saas-backend.onrender.com).

Flow:
  1. GET {SAAS_API_URL}/audio?id=<vid>&api_key=<key>  -> JSON with audio_streams[].url
     (or /video/hq for video)
  2. Each stream URL is a googlevideo videoplayback URL IP-pinned to the EC2 host
     (13.61.0.2). Fetching it MUST egress from that host; from any other IP it 403s.
  3. Stream the chosen URL to disk (GET, not HEAD), retry on 403 (a fresh /audio
     call yields a fresh URL that may work).

Note: on a host whose egress IP is Google-blocklisted this downloader will still
403 on the media fetch -- the same as every other path. It only streams bytes when
the process egresses from 13.61.0.2 (i.e. run on EC2, or behind an EC2 egress proxy).
"""
import os
import ssl
import asyncio

import aiohttp

from AloneX import config, logger


class SaaSAPI:
    def __init__(self):
        self.base = getattr(config, "SAAS_API_URL", None) or "https://youtube-api-saas-backend.onrender.com"
        self.key = getattr(config, "SAAS_API_KEY", None) or "lily_If5GeswRaQESaifBoBxMHlYZVqhJF1Y"
        self.retries = int(getattr(config, "SAAS_RETRIES", 3))
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.session = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _resolve(self, vid_id: str, media_type: str) -> str | None:
        """Return a googlevideo stream URL for the given video, or None."""
        session = await self._get_session()
        endpoint = f"{self.base}/{'video/hq' if media_type == 'video' else 'audio'}"
        try:
            async with session.get(
                endpoint,
                params={"api_key": self.key, "id": vid_id},
                timeout=aiohttp.ClientTimeout(total=40),
                ssl=self.ssl_ctx,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"SaaS resolve HTTP {resp.status} for {vid_id}")
                    return None
                data = await resp.json(content_type=None)
        except Exception as e:
            logger.warning(f"SaaS resolve error for {vid_id}: {e}")
            return None

        if not data.get("success"):
            logger.warning(f"SaaS success=false for {vid_id}: {str(data)[:160]}")
            return None

        streams = None
        if media_type == "video":
            streams = (data.get("stream") or {}).get("url")
            return streams  # single URL
        # audio: choose the highest-bitrate stream
        streams = (data.get("audio") or {}).get("audio_streams") or []
        if not streams:
            return None
        streams = sorted(streams, key=lambda s: float(s.get("audio_bitrate", 0) or 0), reverse=True)
        return streams[0].get("url")

    async def download(self, vid_id: str, video: bool, path: str) -> str | None:
        if not self.key:
            return None
        media_type = "video" if video else "audio"
        for attempt in range(self.retries):
            try:
                url = await self._resolve(vid_id, media_type)
                if not url:
                    continue
                session = await self._get_session()
                try:
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=600), ssl=self.ssl_ctx
                    ) as r:
                        if r.status == 200:
                            with open(path, "wb") as f:
                                async for chunk in r.content.iter_chunked(1024 * 1024):
                                    f.write(chunk)
                            if os.path.exists(path) and os.path.getsize(path) > 1024:
                                logger.info(f"SaaS download OK {vid_id} -> {path}")
                                return path
                            if os.path.exists(path):
                                os.remove(path)
                        else:
                            logger.warning(f"SaaS stream status {r.status} for {vid_id} (attempt {attempt+1})")
                except Exception as e:
                    logger.warning(f"SaaS stream error for {vid_id} (attempt {attempt+1}): {e}")
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"SaaS attempt {attempt+1} error for {vid_id}: {e}")
        return None


async def saas_download(vid_id: str, video: bool = False) -> str | None:
    """Convenience wrapper used by the download chain."""
    os.makedirs("downloads", exist_ok=True)
    path = f"downloads/{vid_id}.{'mp4' if video else 'mp3'}"
    if os.path.exists(path) and os.path.getsize(path) > 1024:
        return path
    api = SaaSAPI()
    try:
        return await api.download(vid_id, video, path)
    finally:
        if api.session and not api.session.closed:
            await api.session.close()
