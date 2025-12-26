import base64
import hashlib
import json
import random
import re
import time
import urllib.parse
import requests

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class HuyaLiveStream(BaseLiveStream):
    """
      A class for fetching and processing Huya live stream information.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        })
        if proxy_addr:
            self.session.proxies.update({'http': proxy_addr, 'https': proxy_addr})

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        return await self.fetch_app_stream_data(url, process_data)

    async def fetch_app_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches app stream data for a live room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        room_id = url.split('?')[0].rsplit('/', maxsplit=1)[-1]

        if any(char.isalpha() for char in room_id):
            html_str = self.session.get(url, timeout=15).text
            match = re.search('ProfileRoom":(.*?),"sPrivateHost', html_str)
            if match:
                room_id = match.group(1)
            else:
                raise Exception('Please use "https://www.huya.com/+room_number" for recording')

        live_url = 'https://www.huya.com/' + str(room_id)

        params = {
            'm': 'Live',
            'do': 'profileRoom',
            'roomid': room_id,
            'showSecret': '1',
        }
        wx_app_api = f'https://mp.huya.com/cache.php?{urllib.parse.urlencode(params)}'
        json_str = self.session.get(wx_app_api, timeout=15).text
        json_data = json.loads(json_str)

        if not process_data:
            return json_data
        anchor_name = json_data['data']['profileInfo']['nick']
        live_status = json_data['data']['realLiveStatus']
        if live_status != 'ON':
            return {'anchor_name': anchor_name, 'is_live': False, 'live_url': live_url}
        else:
            live_title = json_data['data']['liveData']['introduction']

            payload = {
                'appId': 5002,
                'byPass': 3,
                'context': '',
                'version': '2.4',
                'data': {}
            }
            uid_resp = self.session.post(
                'https://udblgn.huya.com/web/anonymousLogin',
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=15
            ).text
            uid = json.loads(uid_resp)['data']['uid']

            base_steam_info_list = json_data['data']['stream']['baseSteamInfoList']
            all_flv_urls = []
            play_url_list = []
            for i in base_steam_info_list:
                cdn_type = i['sCdnType']
                stream_name = i['sStreamName']
                s_flv_url = i['sFlvUrl']
                flv_anti_code = i['sFlvAntiCode']
                s_hls_url = i['sHlsUrl']
                hls_anti_code = i['sHlsAntiCode']

                qr = urllib.parse.parse_qs(flv_anti_code)
                f = str(int(time.time() * 10000))
                ws_time = qr.get('wsTime', [''])[0]
                fm_b64 = qr.get('fm', [''])[0]
                fm_b64 += '=' * (-len(fm_b64) % 4)
                try:
                    fm_raw = base64.b64decode(fm_b64).decode('utf-8')
                except:
                    fm_raw = ''
                fm = fm_raw.replace('$0', str(uid)).replace('$1', stream_name).replace('$2', f).replace('$3', ws_time)
                ws_secret = hashlib.md5(fm.encode('utf-8')).hexdigest()

                flv_params = [
                    f'wsSecret={ws_secret}',
                    f'wsTime={ws_time}',
                    f'u={uid}',
                    f'seqid={f}',
                    f'txyp={qr.get("txyp", [""])[0]}',
                    f'fs={qr.get("fs", [""])[0]}',
                    f'sphdcdn={qr.get("sphdcdn", [""])[0]}',
                    f'sphdDC={qr.get("sphdDC", [""])[0]}',
                    f'sphd={qr.get("sphd", [""])[0]}',
                    f'exsphd={qr.get("exsphd", [""])[0]}',
                    'ratio=0',
                ]
                flv_qs = '&'.join(p for p in flv_params if p.split('=', 1)[1])

                hls_qr = urllib.parse.parse_qs(hls_anti_code)
                hls_ws_time = hls_qr.get('wsTime', [''])[0]
                hls_fm_b64 = hls_qr.get('fm', [''])[0]
                hls_fm_b64 += '=' * (-len(hls_fm_b64) % 4)
                try:
                    hls_fm_raw = base64.b64decode(hls_fm_b64).decode('utf-8')
                except:
                    hls_fm_raw = ''
                hls_fm = hls_fm_raw.replace('$0', str(uid)).replace('$1', stream_name).replace('$2', f).replace('$3', hls_ws_time)
                hls_ws_secret = hashlib.md5(hls_fm.encode('utf-8')).hexdigest()

                hls_params = [
                    f'wsSecret={hls_ws_secret}',
                    f'wsTime={hls_ws_time}',
                    f'u={uid}',
                    f'seqid={f}',
                    f'txyp={hls_qr.get("txyp", [""])[0]}',
                    f'fs={hls_qr.get("fs", [""])[0]}',
                    f'sphdcdn={hls_qr.get("sphdcdn", [""])[0]}',
                    f'sphdDC={hls_qr.get("sphdDC", [""])[0]}',
                    f'sphd={hls_qr.get("sphd", [""])[0]}',
                    f'exsphd={hls_qr.get("exsphd", [""])[0]}',
                    'ratio=0',
                ]
                hls_qs = '&'.join(p for p in hls_params if p.split('=', 1)[1])

                m3u8_url = f'{s_hls_url}/{stream_name}.m3u8?{hls_qs}'.replace('http://', 'https://')
                flv_url = f'{s_flv_url}/{stream_name}.flv?{flv_qs}'.replace('http://', 'https://')

                play_url_list.append(
                    {
                        'cdn_type': cdn_type,
                        'm3u8_url': m3u8_url,
                        'flv_url': flv_url,
                    }
                )
                if flv_url not in all_flv_urls:
                    all_flv_urls.append(flv_url)

            select_item = None
            for item in play_url_list:
                if item["cdn_type"] == "TX":
                    select_item = item
                    break
            select_item = select_item or play_url_list[0]
            m3u8_url = select_item.get("m3u8_url")
            flv_url = select_item.get("flv_url")

            if flv_url in all_flv_urls:
                all_flv_urls.remove(flv_url)

            return {
                'anchor_name': anchor_name,
                'is_live': True,
                'm3u8_url': m3u8_url,
                'flv_url': flv_url,
                'record_url': flv_url or m3u8_url,
                'title': live_title,
                'live_url': live_url,
                'extra': {
                    'backup_url_list': all_flv_urls
                }
            }

    @staticmethod
    async def fetch_stream_url(json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
         Fetches the stream URL for a live room and wraps it into a StreamData object.
         """
        platform = "虎牙直播"
        if 'is_live' in json_data:
            json_data |= {"platform": platform, "quality": video_quality}
            return wrap_stream(json_data)
        return wrap_stream({"platform": platform})
