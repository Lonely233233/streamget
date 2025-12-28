import base64
import hashlib
import json
import re
import time
import urllib.parse

import requests

from ...data import StreamData, wrap_stream
from ..base import BaseLiveStream


class HuyaLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Huya live stream information.
    """

    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/127.0.0.0 Safari/537.36"
                ),
            }
        )
        if proxy_addr:
            self.session.proxies.update({"http": proxy_addr, "https": proxy_addr})

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """Web endpoint fallback - unified to app interface."""
        return await self.fetch_app_stream_data(url, process_data)

    async def fetch_app_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetch live stream data using the mini-program API and generate real URLs
        with the latest anti-leech method (valid as of late 2025).
        """
        room_id = url.split("?")[0].rsplit("/", maxsplit=1)[-1].strip("/")

        if not room_id.isdigit():
            try:
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
                html_str = resp.text

                match = re.search(
                    r'<link\s+[^>]*rel=["\']canonical["\'][^>]*href=["\']https?://www\.huya\.com/(\d+)["\']',
                    html_str,
                    re.IGNORECASE,
                )
                if match:
                    room_id = match.group(1)
                else:
                    match = re.search(
                        r'<meta\s+[^>]*property=["\']og:url["\'][^>]*content=["\']https?://www\.huya\.com/(\d+)["\']',
                        html_str,
                        re.IGNORECASE,
                    )
                    if match:
                        room_id = match.group(1)
                    else:
                        match = re.search(r'"lProfileRoom"\s*:\s*(\d+)', html_str)
                        if match:
                            room_id = match.group(1)
                        else:
                            raise Exception(
                                "无法解析别名房间号，请检查网址是否正确或尝试使用数字房间号"
                            )

            except requests.RequestException as e:
                raise Exception(f"获取房间页面失败: {e}")

        live_url = "https://www.huya.com/" + str(room_id)

        params = {
            "m": "Live",
            "do": "profileRoom",
            "roomid": room_id,
            "showSecret": "1",
        }
        wx_app_api = f"https://mp.huya.com/cache.php?{urllib.parse.urlencode(params)}"
        json_str = self.session.get(wx_app_api, timeout=15).text
        json_data = json.loads(json_str)

        if not process_data:
            return json_data

        anchor_name = json_data["data"]["profileInfo"]["nick"]
        live_status = json_data["data"]["realLiveStatus"]
        live_title = json_data["data"]["liveData"]["introduction"]

        if live_status != "ON":
            return {
                "anchor_name": anchor_name,
                "is_live": False,
                "live_url": live_url,
            }

        return {
            "raw_data": json_data,
            "anchor_name": anchor_name,
            "title": live_title,
            "live_url": live_url,
        }

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
         Fetches the stream URL for a live room and wraps it into a StreamData object.
         """
        platform = "虎牙直播"

        if "raw_data" not in json_data:
            result = {
                "platform": platform,
                "anchor_name": json_data.get("anchor_name", ""),
                "is_live": False,
                "live_url": json_data.get("live_url", ""),
            }
            if video_quality:
                result["quality"] = video_quality
            return wrap_stream(result)

        raw_data = json_data["raw_data"]
        anchor_name = json_data["anchor_name"]
        live_title = json_data["title"]
        live_url = json_data["live_url"]

        payload = {
            "appId": 5002,
            "byPass": 3,
            "context": "",
            "version": "2.4",
            "data": {},
        }
        uid_resp = requests.post(
            "https://udblgn.huya.com/web/anonymousLogin",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        ).text
        uid = json.loads(uid_resp)["data"]["uid"]

        base_steam_info_list = raw_data["data"]["stream"]["baseSteamInfoList"]
        play_url_list = []
        all_flv_urls = []

        f = str(int(time.time() * 10000))

        quality_list = ["OD", "UHD", "HD", "SD", "LD"]

        if not video_quality:
            video_quality = "OD"
        else:
            if str(video_quality).isdigit():
                try:
                    video_quality = quality_list[int(video_quality)]
                except IndexError:
                    video_quality = "OD"
            else:
                video_quality = video_quality.upper()

        if video_quality == "OD":
            target_ratio = "0"
        elif video_quality == "UHD":
            target_ratio = "8000"
        elif video_quality == "HD":
            target_ratio = "4000"
        elif video_quality == "SD":
            target_ratio = "2000"
        elif video_quality == "LD":
            target_ratio = "500"
        else:
            target_ratio = "0"

        for i in base_steam_info_list:
            cdn_type = i["sCdnType"]
            stream_name = i["sStreamName"]
            s_flv_url = i["sFlvUrl"]
            flv_anti_code = i["sFlvAntiCode"]

            qr = urllib.parse.parse_qs(flv_anti_code)
            ws_time = qr.get("wsTime", [""])[0]
            fm_b64 = qr.get("fm", [""])[0]
            fm_b64 += "=" * (-len(fm_b64) % 4)
            try:
                fm_raw = base64.b64decode(fm_b64).decode("utf-8")
            except Exception:
                fm_raw = ""
            fm = (
                fm_raw.replace("$0", str(uid))
                .replace("$1", stream_name)
                .replace("$2", f)
                .replace("$3", ws_time)
            )
            ws_secret = hashlib.md5(fm.encode("utf-8")).hexdigest()

            flv_params = [
                f"wsSecret={ws_secret}",
                f"wsTime={ws_time}",
                f"u={uid}",
                f"seqid={f}",
                f"txyp={qr.get('txyp', [''])[0]}",
                f"fs={qr.get('fs', [''])[0]}",
                f"sphdcdn={qr.get('sphdcdn', [''])[0]}",
                f"sphdDC={qr.get('sphdDC', [''])[0]}",
                f"sphd={qr.get('sphd', [''])[0]}",
                f"exsphd={qr.get('exsphd', [''])[0]}",
                f"ratio={target_ratio}",
            ]
            flv_qs = "&".join(p for p in flv_params if p.split("=", 1)[1])

            flv_url = f"{s_flv_url}/{stream_name}.flv?{flv_qs}".replace("http://", "https://")

            play_url_list.append(
                {
                    "cdn_type": cdn_type,
                    "flv_url": flv_url,
                }
            )
            if flv_url not in all_flv_urls:
                all_flv_urls.append(flv_url)

        flv_url = play_url_list[0]["flv_url"] if play_url_list else ""

        if flv_url in all_flv_urls:
            all_flv_urls.remove(flv_url)

        result = {
            "platform": platform,
            "anchor_name": anchor_name,
            "is_live": True,
            "flv_url": flv_url,
            "record_url": flv_url,
            "title": live_title,
            "live_url": live_url,
            "quality": video_quality,
            "extra": {
                "backup_url_list": all_flv_urls,
            },
        }
        return wrap_stream(result)
