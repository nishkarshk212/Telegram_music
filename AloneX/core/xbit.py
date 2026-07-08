# ALONE-CODER
import aiohttp
import os
import ssl
from AloneX import logger

class XBitAPI:
    def __init__(self):
        from AloneX import config
        self.xbit_api_key = config.XBIT_API_TOKEN
        self.xbit_base_url = config.XBIT_API_URL
        self.aru_api_key = config.ARU_API_KEY
        self.aru_base_url = config.ARU_API_URL
        # Create SSL context that ignores certificate errors
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        # Reuse a single session for all requests to speed things up
        self.session = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_info(self, vid_id: str):
        # Try XBit first (working!)
        if self.xbit_api_key and self.xbit_base_url:
            endpoint = f"{self.xbit_base_url}/info/{vid_id}"
            headers = {
                'x-api-key': self.xbit_api_key,
                'Content-Type': 'application/json'
            }
            try:
                session = await self._get_session()
                async with session.get(endpoint, headers=headers, timeout=aiohttp.ClientTimeout(total=5), ssl=self.ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "success":
                            return data
            except Exception as e:
                logger.error(f"Error fetching from XBit API: {e}")
        
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
        
        # Try XBit first with direct URL - download the file
        if self.xbit_api_key and self.xbit_base_url:
            session = await self._get_session()
            for retry in range(20):  # Try up to 20 attempts to get a fresh URL
                try:
                    logger.info(f"XBit download attempt {retry+1} for {vid_id}")
                    info = await self.get_info(vid_id)
                    if info:
                        url_key = 'video_url' if video else 'audio_url'
                        if url_key in info and info[url_key]:
                            direct_url = info[url_key]
                            logger.info(f"Got URL, starting download NOW for {vid_id}")
                            headers = {}
                            if self.xbit_api_key and "xbitcode.com" in direct_url:
                                headers["x-api-key"] = self.xbit_api_key
                            
                            # Start download immediately
                            async with session.get(direct_url, headers=headers, timeout=aiohttp.ClientTimeout(total=600), ssl=self.ssl_context) as response:
                                if response.status == 200:
                                    with open(path, "wb") as f:
                                        async for chunk in response.content.iter_chunked(1024 * 1024):
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
                                            logger.warning(f"XBit URL expired on attempt {retry+1}, retrying NOW...")
                                            continue
                                        else:
                                            logger.error(f"XBit direct URL download failed! Status: {response.status}, Body: {error_body}, URL: {direct_url}")
                                            break
                                else:
                                    error_body = await response.text()
                                    logger.error(f"XBit direct URL download failed! Status: {response.status}, Body: {error_body}, URL: {direct_url}")
                                    break
                except Exception as e:
                    logger.error(f"Error downloading from XBit API on attempt {retry+1}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except:
                            pass
        
        # Fallback to ARU
        if self.aru_api_key and self.aru_base_url:
            direct_url = f"{self.aru_base_url}/download?url={youtube_url}&type={'video' if video else 'audio'}&api_key={self.aru_api_key}"
            try:
                logger.info(f"Trying to download {vid_id} using ARU API")
                session = await self._get_session()
                async with session.get(direct_url, timeout=aiohttp.ClientTimeout(total=600), ssl=self.ssl_context) as response:
                    if response.status == 200:
                        with open(path, "wb") as f:
                            async for chunk in response.content.iter_chunked(1024 * 1024):
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
        
        # Fallback to YouTube
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
