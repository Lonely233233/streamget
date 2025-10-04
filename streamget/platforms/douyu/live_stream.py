import asyncio
import hashlib
import json
import re
import time

import execjs

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req
from ..base import BaseLiveStream


class DouyuLiveStream(BaseLiveStream):
    """
    A class for fetching and processing Douyu live stream information, including live and recorded streams.
    """
    def __init__(self, proxy_addr: str | None = None, cookies: str | None = None):
        super().__init__(proxy_addr, cookies)
        self.mobile_headers = self._get_mobile_headers()
        self.pc_headers = self._get_pc_headers()

    def _get_mobile_headers(self) -> dict:
        return {
            'user-agent': 'ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))',
            'cookie': self.cookies or '',
            'referer': 'https://m.douyu.com/3125893?rid=3125893&dyshid=0-96003918aa5365bc6dcb4933000316p1&dyshci=181',
            'accept-encoding': 'gzip, deflate, br',
        }

    def _get_pc_headers(self) -> dict:
        return {
            'user-agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ),
            'cookie': self.cookies or '',
            'accept-encoding': 'gzip, deflate, br',
        }

    @staticmethod
    def _get_md5(data) -> str:
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    async def _get_token_js(self, rid: str, did: str) -> list[str]:
        url = f'https://www.douyu.com/{rid}'
        for attempt in range(3):
            try:
                html_str = await async_req(url=url, proxy_addr=self.proxy_addr, headers=self.pc_headers)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
        result = re.search(r'(vdwdae325w_64we[\s\S]*function ub98484234[\s\S]*?)function', html_str).group(1)
        func_ub9 = re.sub(r'eval.*?;}', 'strc;}', result)
        js = execjs.compile(func_ub9)
        res = js.call('ub98484234')

        t10 = str(int(time.time()))
        v = re.search(r'v=(\d+)', res).group(1)
        rb = self._get_md5(str(rid) + str(did) + str(t10) + str(v))

        func_sign = re.sub(r'return rt;}\);?', 'return rt;}', res)
        func_sign = func_sign.replace('(function (', 'function sign(')
        func_sign = func_sign.replace('CryptoJS.MD5(cb).toString()', '"' + rb + '"')

        try:
            js = execjs.compile(func_sign)
            params = js.call('sign', rid, did, t10)
            params_list = re.findall('=(.*?)(?=&|$)', params)
            return params_list
        except execjs.ProgramError:
            raise execjs.ProgramError('Failed to execute JS code. Please check if the Node.js environment')

    async def _fetch_web_stream_url(self, rid: str, rate: str = '-1', cdn: str | None = None) -> dict:
        did = '10000000000000000000000000003306'
        params_list = await self._get_token_js(rid, did)
        data = {
            'v': params_list[0],
            'did': params_list[1],
            'tt': params_list[2],
            'sign': params_list[3],
            'ver': '22011191',
            'rid': rid,
            'rate': rate,
        }
        if cdn:
            data['cdn'] = cdn

        app_api = f'https://www.douyu.com/lapi/live/getH5Play/{rid}'
        for attempt in range(3):
            try:
                json_str = await async_req(
                    url=app_api,
                    proxy_addr=self.proxy_addr,
                    headers=self.mobile_headers,
                    data=data
                )
                json_data = json.loads(json_str)
                return json_data
            except Exception as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> dict:
        """
        Fetches web stream data for a live or recorded room.

        Args:
            url (str): The room URL.
            process_data (bool): Whether to process the data. Defaults to True.

        Returns:
            dict: A dictionary containing anchor name, live status, room URL, and title.
        """
        match_rid = re.search(r'(?:rid=(.*?)(?=&|$)|douyu\.com/(.*?)(?=\?|$))', url)
        if match_rid:
            rid = match_rid.group(1) or match_rid.group(2)
        else:
            raise ValueError("Invalid URL: Unable to extract room ID")
        
        if not match_rid.group(1):
            html_str = await async_req(url=f'https://m.douyu.com/{rid}', proxy_addr=self.proxy_addr,
                                       headers=self.pc_headers)
            json_str = re.findall('<script id="vike_pageContext" type="application/json">(.*?)</script>', html_str)[0]
            json_data = json.loads(json_str)
            rid = json_data['pageProps']['room']['roomInfo']['roomInfo']['rid']

        url2 = f'https://www.douyu.com/betard/{rid}'
        json_str = await async_req(url2, proxy_addr=self.proxy_addr, headers=self.pc_headers)
        json_data = json.loads(json_str)
        if not process_data:
            return json_data
        result = {
            "anchor_name": json_data['room']['nickname'],
            "is_live": False,
            "live_url": url
        }
        if json_data['room']['videoLoop'] == 0 and json_data['room']['show_status'] == 1:
            result["title"] = json_data['room']['room_name'].replace('&nbsp;', '')
            result["is_live"] = True
            result["room_id"] = json_data['room']['room_id']
        else:
            result["room_id"] = json_data['room'].get('room_id')
            result["title"] = json_data['room'].get('room_name', '').replace('&nbsp;', '')
        return result

    async def fetch_stream_url(self, json_data: dict, video_quality: str | int | None = None) -> StreamData:
        """
        Fetches the stream URL for a live or recorded room and wraps it into a StreamData object,
        including backup CDN streams.
        """
        platform = '斗鱼直播'
        video_quality_options = {
            "OD": '0',
            "BD": '0',
            "UHD": '3',
            "HD": '2',
            "SD": '1',
            "LD": '1'
        }
        rid = str(json_data["room_id"])
        json_data.pop("room_id")

        if not video_quality:
            video_quality = "OD"
        else:
            if str(video_quality).isdigit():
                video_quality = list(video_quality_options.keys())[int(video_quality)]
            else:
                video_quality = video_quality.upper()

        rate = video_quality_options.get(video_quality, '0')
        
        flv_data = await self._fetch_web_stream_url(rid=rid, rate=rate)
        rtmp_url = flv_data['data'].get('rtmp_url')
        rtmp_live = flv_data['data'].get('rtmp_live')
        
        urls = []
        if rtmp_url and rtmp_live:
            urls.append(f'{rtmp_url}/{rtmp_live}')

        cdns_with_name = flv_data.get('data', {}).get('cdnsWithName', [])
        rtmp_cdn = flv_data.get('data', {}).get('rtmp_cdn')
        tasks = [
            self._fetch_web_stream_url(rid=rid, rate=rate, cdn=item['cdn'])
            for item in cdns_with_name if item.get('cdn') and item['cdn'] != rtmp_cdn
        ]
        backup_results = await asyncio.gather(*tasks, return_exceptions=True)
        for backup_data in backup_results:
            if isinstance(backup_data, dict):
                backup_rtmp_url = backup_data.get('data', {}).get('rtmp_url')
                backup_rtmp_live = backup_data.get('data', {}).get('rtmp_live')
                if backup_rtmp_url and backup_rtmp_live:
                    urls.append(f'{backup_rtmp_url}/{backup_rtmp_live}')

        json_data |= {
            "platform": platform,
            "quality": video_quality,
            "flv_url": urls[0] if urls else None,
            "record_url": urls[1] if len(urls) > 1 else (urls[0] if urls else None)
        }
        
        return wrap_stream(json_data)
