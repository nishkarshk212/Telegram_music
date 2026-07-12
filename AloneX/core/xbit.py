# ALONE-CODER
import aiohttp
import os
import ssl
import asyncio
import json
from AloneX import logger


class XBitAPI:
    def __init__(self):
        from AloneX import config
        self.xbit_api_key = config.XBIT_API_TOKEN
        self.xbit_base_url = config.XBIT_API_URL
        self.aru_api_key = config.ARU_API_KEY
        self.aru_base_url = config.ARU_API_URL
        # Working Railway proxy (youtube-api-music-production-824b.up.railway.app)
        self.yt_api_key = config.YOUTUBE_API_KEY
        self.yt_api_base = config.YOUTUBE_API_BASE_URL
        # Create SSL context that ignores certificate errors
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        # Reuse a single session for all requests to speed things up
        self.session = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(limit=50)
            self.session = aiohttp.ClientSession(connector=connector)
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # ------------------------------------------------------------------
    # Working Railway proxy (824b.up.railway.app) -- primary path
    # Response: {"success":true,"download":{"best_audio_url":...,"best_video_url":...}}
    # Auth: X-API-Key header. Always GET the googlevideo URL (HEAD -> 405).
    # The proxy backend is intermittent (some googlevideo URLs 403), so we
    # retry the whole fetch+download a few times -- a fresh call often yields
    # a working URL.
    # ------------------------------------------------------------------
    async def download_via_proxy(self, vid_id: str, video: bool, path: str, attempts: int = 3):
        if not (self.yt_api_key and self.yt_api_base):
            return None
        session = await self._get_session()
        for i in range(attempts):
            try:
                endpoint = f"{self.yt_api_base}/download?id={vid_id}&type={'video' if video else 'audio'}"
                headers = {"X-API-Key": self.yt_api_key, "Content-Type": "application/json"}
                async with session.get(
                    endpoint, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=40), ssl=self.ssl_context,
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Proxy HTTP {resp.status} for {vid_id} (attempt {i+1})")
                        continue
                    data = await resp.json()
                    if not data.get("success"):
                        logger.warning(f"Proxy success=false for {vid_id}: {str(data)[:160]}")
                        continue
                    dl = data.get("download", {})
                    url = dl.get("best_audio_url") or dl.get("best_video_url")
                    if not url:
                        logger.warning(f"Proxy returned no URL for {vid_id}")
                        continue
                    logger.info(f"Proxy URL for {vid_id}, downloading via GET (attempt {i+1})")
                    try:
                        async with session.get(
                            url, timeout=aiohttp.ClientTimeout(total=600), ssl=self.ssl_context,
                        ) as r:
                            if r.status == 200:
                                with open(path, "wb") as f:
                                    async for chunk in r.content.iter_chunked(1024 * 1024):
                                        f.write(chunk)
                                if os.path.exists(path) and os.path.getsize(path) > 1024:
                                    return path
                                if os.path.exists(path):
                                    os.remove(path)
                            else:
                                logger.warning(f"Proxy stream status {r.status} for {vid_id} (attempt {i+1})")
                    except Exception as e:
                        logger.warning(f"Proxy stream error for {vid_id} (attempt {i+1}): {e}")
                        if os.path.exists(path):
                            try:
                                os.remove(path)
                            except Exception:
                                pass
            except Exception as e:
                logger.warning(f"Proxy download error for {vid_id} (attempt {i+1}): {e}")
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
        return None

    async def _get_single_info(self, session, vid_id):
        try:
            endpoint = f"{self.xbit_base_url}/info/{vid_id}"
            headers = {
                'x-api-key': self.xbit_api_key,
                'Content-Type': 'application/json'
            }
            async with session.get(endpoint, headers=headers, timeout=aiohttp.ClientTimeout(total=3), ssl=self.ssl_context) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return data
        except Exception as e:
            pass
        return None

    async def get_info(self, vid_id: str):
        # Try XBit first
        if self.xbit_api_key and self.xbit_base_url:
            session = await self._get_session()
            # Make 5 concurrent requests to get_info, return the first successful one
            tasks = [asyncio.create_task(self._get_single_info(session, vid_id)) for _ in range(5)]
            for future in asyncio.as_completed(tasks):
                result = await future
                if result:
                    # Cancel remaining tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    return result
        return None

    async def search(self, query: str, message_id: int, video: bool = False):
        return None  # No working search endpoint yet

    async def playlist(self, limit: int, mention: str, url: str, video: bool = False):
        return None  # No working playlist endpoint yet

    async def download(self, vid_id: str, video: bool = False):
        os.makedirs("downloads", exist_ok=True)
        path = f"downloads/{vid_id}.{'mp4' if video else 'mp3'}"
        if os.path.exists(path) and os.path.getsize(path) > 1024:
            logger.info(f"File already exists: {path}")
            return path

        youtube_url = f"https://www.youtube.com/watch?v={vid_id}"

        # 1) Working Railway proxy FIRST (retries internally for intermittent 403s)
        logger.info(f"Trying Railway proxy for {vid_id}")
        res = await self.download_via_proxy(vid_id, video, path)
        if res:
            logger.info(f"Successfully downloaded {vid_id} via Railway proxy")
            return res

        # 2) XBit (currently down -- only a couple of quick attempts, then bail)
        if self.xbit_api_key and self.xbit_base_url:
            session = await self._get_session()
            for attempt in range(2):  # trimmed from 20: XBit is dead, don't stall
                try:
                    logger.info(f"XBit download attempt {attempt+1} for {vid_id}")
                    info = await self.get_info(vid_id)
                    if info:
                        url_key = 'video_url' if video else 'audio_url'
                        if url_key in info and info[url_key]:
                            direct_url = info[url_key]
                            logger.info(f"Got URL, starting download NOW for {vid_id}")
                            headers = {}
                            if self.xbit_api_key and "xbitcode.com" in direct_url:
                                headers["x-api-key"] = self.xbit_api_key

                            async with session.get(direct_url, headers=headers, timeout=aiohttp.ClientTimeout(total=600), ssl=self.ssl_context) as response:
                                if response.status == 200:
                                    with open(path, "wb") as f:
                                        async for chunk in response.content.iter_chunked(1024*1024):
                                            f.write(chunk)
                                    if os.path.exists(path) and os.path.getsize(path) > 1024:
                                        logger.info(f"Successfully downloaded {vid_id} using XBit API")
                                        return path
                                    else:
                                        logger.error(f"Downloaded file is too small for {vid_id}, cleaning up...")
                                        if os.path.exists(path):
                                            os.remove(path)
                                elif response.status == 410:
                                    error_body = await response.text()
                                    if "URL_EXPIRED" in error_body:
                                        logger.warning(f"XBit URL expired on attempt {attempt+1}, retrying NOW...")
                                        continue
                                    else:
                                        logger.error(f"XBit direct URL download failed! Status: {response.status}, Body: {error_body}, URL: {direct_url}")
                                        break
                                else:
                                    error_body = await response.text()
                                    logger.error(f"XBit direct URL download failed! Status: {response.status}, Body: {error_body}, URL: {direct_url}")
                                    break
                except Exception as e:
                    logger.error(f"Error downloading from XBit API on attempt {attempt+1}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except:
                            pass

        # 3) Fallback to ARU
        if self.aru_api_key and self.aru_base_url:
            direct_url = f"{self.aru_base_url}/download?url={youtube_url}&type={'video' if video else 'audio'}&api_key={self.aru_api_key}"
            try:
                logger.info(f"Trying to download {vid_id} using ARU API")
                session = await self._get_session()
                async with session.get(direct_url, timeout=aiohttp.ClientTimeout(total=600), ssl=self.ssl_context) as response:
                    if response.status == 200:
                        with open(path, "wb") as f:
                            async for chunk in response.content.iter_chunked(1024*1024):
                                f.write(chunk)
                        if os.path.exists(path) and os.path.getsize(path) > 1024:
                            logger.info(f"Successfully downloaded {vid_id} using ARU API")
                            return path
                        else:
                            logger.error(f"Downloaded file is too small for {vid_id}, cleaning up...")
                            if os.path.exists(path):
                                os.remove(path)
            except Exception as e:
                logger.error(f"Error downloading from ARU API: {e}")
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

        # 4) Fallback to YouTube (yt-dlp) -- usually bot-blocked
        logger.info(f"Falling back to YouTube download for {vid_id}...")
        from AloneX import yt
        try:
            result = await yt.download(vid_id, video=video)
            if result:
                logger.info(f"YouTube download successful: {result}")
            else:
                logger.error(f"YouTube download failed for {vid_id}")
            return result
        except Exception as e:
            logger.error(f"Error in YouTube download fallback: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
