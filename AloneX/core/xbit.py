# ALONE-CODER
import aiohttp

class XBitAPI:
    def __init__(self):
        from AloneX import config
        self.xbit_api_key = config.XBIT_API_TOKEN
        self.xbit_base_url = config.XBIT_API_URL
        self.aru_api_key = config.ARU_API_KEY
        self.aru_base_url = config.ARU_API_URL

    async def get_info(self, vid_id: str):
        # Try XBit first (working!)
        if self.xbit_api_key and self.xbit_base_url:
            endpoint = f"{self.xbit_base_url}/info/{vid_id}"
            headers = {
                'x-api-key': self.xbit_api_key,
                'Content-Type': 'application/json'
            }
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(endpoint, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('status') == 'success':
                                return data
            except Exception as e:
                print(f"Error fetching from XBit API: {e}")
        
        return None

    async def search(self, query: str, message_id: int, video: bool = False):
        return None  # No working search endpoint yet

    async def playlist(self, limit: int, mention: str, url: str, video: bool = False):
        return None  # No working playlist endpoint yet

    async def download(self, vid_id: str, video: bool = False):
        import os
        path = f"downloads/{vid_id}.{'mp4' if video else 'mp3'}"
        if os.path.exists(path):
            return path

        youtube_url = f"https://www.youtube.com/watch?v={vid_id}"
        
        # Try XBit first with direct URL - download the file
        if self.xbit_api_key and self.xbit_base_url:
            try:
                info = await self.get_info(vid_id)
                if info:
                    url_key = 'video_url' if video else 'audio_url'
                    if url_key in info and info[url_key]:
                        direct_url = info[url_key]
                        print(f"Successfully got direct URL for {vid_id} using XBit API, downloading...")
                        headers = {}
                        if self.xbit_api_key and "xbitcode.com" in direct_url:
                            headers["x-api-key"] = self.xbit_api_key
                        async with aiohttp.ClientSession() as session:
                            async with session.get(direct_url, headers=headers, timeout=300) as response:
                                if response.status == 200:
                                    with open(path, "wb") as f:
                                        async for chunk in response.content.iter_chunked(1024 * 1024):
                                            f.write(chunk)
                                    if os.path.exists(path) and os.path.getsize(path) > 1024:
                                        print(f"Successfully downloaded {vid_id} using XBit API")
                                        return path
                                else:
                                    error_body = await response.text()
                                    print(f"XBit direct URL download failed! Status: {response.status}, Body: {error_body}, URL: {direct_url}")
            except Exception as e:
                print(f"Error downloading from XBit API: {e}")
        
        # Fallback to ARU
        if self.aru_api_key and self.aru_base_url:
            direct_url = f"{self.aru_base_url}/download?url={youtube_url}&type={'video' if video else 'audio'}&api_key={self.aru_api_key}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(direct_url, timeout=300) as response:
                        if response.status == 200:
                            with open(path, "wb") as f:
                                async for chunk in response.content.iter_chunked(1024 * 1024):
                                    f.write(chunk)
                            if os.path.exists(path) and os.path.getsize(path) > 1024:
                                print(f"Successfully downloaded {vid_id} using ARU API")
                                return path
            except Exception as e:
                print(f"Error downloading from ARU API: {e}")
        
        # Fallback to yt-dlp
        print(f"Falling back to YouTube download for {vid_id}...")
        from AloneX import yt
        return await yt.download(vid_id, video=video)
