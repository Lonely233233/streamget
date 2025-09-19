import json
import re
import urllib.parse
from typing import Dict, List, Optional

from ...data import StreamData, wrap_stream
from ...requests.async_http import async_req, get_response_status
from ..base import BaseLiveStream
from .utils import DouyinUtils, UnsupportedUrlError


class StreamDataSorter:
    
    @staticmethod
    def sort_streams_by_bitrate(data: Dict) -> List[Dict]:
        streams = []
        for quality, stream_info in data.items():
            try:
                main = stream_info.get("main")
                if not main:
                    continue

                sdk_params_str = main.get("sdk_params")
                if not sdk_params_str:
                    continue

                sdk_params = json.loads(sdk_params_str) if isinstance(sdk_params_str, str) else sdk_params_str
                vbitrate = sdk_params.get("vbitrate")
                if not isinstance(vbitrate, (int, float)) or vbitrate <= 0:
                    continue

                flv_url = main.get("flv", "")
                hls_url = main.get("hls", "")
                if not flv_url and not hls_url:
                    continue

                streams.append({
                    "name": quality,
                    "bitrate": int(vbitrate),
                    "flv": flv_url,
                    "hls": hls_url
                })
            except (json.JSONDecodeError, Exception):
                continue

        return sorted(streams, key=lambda x: x["bitrate"], reverse=True)


class WebStreamDataFetcher:
    
    def __init__(self, proxy_addr: Optional[str], headers: Dict, stream_orientation: int):
        self.proxy_addr = proxy_addr
        self.headers = headers
        self.stream_orientation = stream_orientation
        self.stream_data_sorter = StreamDataSorter()

    async def fetch(self, web_rid: str, process_data: bool = True) -> Dict:
        params = {
            "aid": "6383",
            "app_name": "douyin_web",
            "live_id": "1",
            "device_platform": "web",
            "language": "zh-CN",
            "browser_language": "zh-CN",
            "browser_platform": "Win32",
            "browser_name": "Chrome",
            "browser_version": "116.0.0.0",
            "web_rid": web_rid,
            'is_need_double_stream': 'false',
            'msToken': '',
            'a_bogus': ''
        }
        api = 'https://live.douyin.com/webcast/room/web/enter/?' + urllib.parse.urlencode(params)
        json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.headers)
        
        if not process_data:
            return json.loads(json_str)
        
        json_data = json.loads(json_str)['data']
        if not json_data.get('data'):
            raise Exception("live data fetch error")
        
        room_data = json_data['data'][0]
        room_data['anchor_name'] = json_data['user']['nickname']
        room_data['live_url'] = f"https://live.douyin.com/{web_rid}"

        if room_data.get('status') == 4:
            return room_data
        
        stream_orientation = room_data['stream_url']['stream_orientation']
        pull_datas = room_data['stream_url'].get('pull_datas')
        orientation = 2 if stream_orientation == 2 and self.stream_orientation == 2 and pull_datas else 1

        if orientation == 2:
            stream_data_str = list(room_data['stream_url']['pull_datas'].values())[0]['stream_data']
            stream_data = json.loads(stream_data_str)
            sorted_stream_data = self.stream_data_sorter.sort_streams_by_bitrate(stream_data["data"])
            hls_pull_url_map = {i["name"]: i['hls'] for i in sorted_stream_data}
            flv_pull_url_map = {i["name"]: i['flv'] for i in sorted_stream_data}
            room_data['stream_url']['hls_pull_url_map'] = hls_pull_url_map
            room_data['stream_url']['flv_pull_url'] = flv_pull_url_map
            return room_data
        else:
            stream_data = room_data['stream_url']['live_core_sdk_data']['pull_data']['stream_data']
            origin_data = json.loads(stream_data)['data']['origin']['main']
            sdk_params = json.loads(origin_data['sdk_params'])
            origin_hls_codec = sdk_params.get('VCodec') or ''
            origin_m3u8 = {'ORIGIN': f"{origin_data['hls']}&codec={origin_hls_codec}"}
            origin_flv = {'ORIGIN': f"{origin_data['flv']}&codec={origin_hls_codec}"}
            hls_pull_url_map = room_data['stream_url']['hls_pull_url_map']
            flv_pull_url = room_data['stream_url']['flv_pull_url']
            room_data['stream_url']['hls_pull_url_map'] = {**origin_m3u8, **hls_pull_url_map}
            room_data['stream_url']['flv_pull_url'] = {**origin_flv, **flv_pull_url}
            return room_data


class AppStreamDataFetcher:
    
    def __init__(self, proxy_addr: Optional[str], headers: Dict, stream_orientation: int):
        self.proxy_addr = proxy_addr
        self.headers = headers
        self.stream_orientation = stream_orientation
        self.web_stream_fetcher = WebStreamDataFetcher(proxy_addr, headers, stream_orientation)
        self.douyin_utils = DouyinUtils()

    async def fetch(self, url: str, process_data: bool = True) -> Dict:
        url = url.strip()
        try:
            if self.stream_orientation == 2:
                html_str = await async_req(url, proxy_addr=self.proxy_addr, headers=self.headers)
                web_rid_match = re.search(r'webRid(.*?)desensitizedNickname', html_str)
                if not web_rid_match:
                    raise Exception("Failed to extract web_rid")
                web_rid = re.search(r'(\d+)', web_rid_match.group(1)).group(1)
                return await self.web_stream_fetcher.fetch(web_rid, process_data)

            room_id, sec_uid = await self.douyin_utils.get_sec_user_id(url, proxy_addr=self.proxy_addr)
            app_params = {
                "verifyFp": "verify_lxj5zv70_7szNlAB7_pxNY_48Vh_ALKF_GA1Uf3yteoOY",
                "type_id": "0",
                "live_id": "1",
                "room_id": room_id,
                "sec_user_id": sec_uid,
                "version_code": "99.99.99",
                "app_id": "1128",
                "is_need_double_stream": True
            }
            api = 'https://webcast.amemv.com/webcast/room/reflow/info/?' + urllib.parse.urlencode(app_params)
            json_str = await async_req(api, proxy_addr=self.proxy_addr, headers=self.headers)
            
            if not process_data:
                return json.loads(json_str)
            
            json_data = json.loads(json_str)['data']
            room_data = json_data.get('room')
            if not room_data:
                raise Exception("VR live is not supported")
            
            owner_data = room_data['owner']
            room_data['anchor_name'] = owner_data['nickname']
            web_rid = owner_data.get('web_rid')
            room_data['live_url'] = f"https://live.douyin.com/{web_rid}" if web_rid else None
            stream_data = room_data['stream_url']['live_core_sdk_data']['pull_data']['stream_data']
            origin_data = json.loads(stream_data)['data']['origin']['main']
            sdk_params = json.loads(origin_data['sdk_params'])
            origin_hls_codec = sdk_params.get('VCodec') or ''
            origin_m3u8 = {'ORIGIN': f"{origin_data['hls']}&codec={origin_hls_codec}"}
            origin_flv = {'ORIGIN': f"{origin_data['flv']}&codec={origin_hls_codec}"}
            hls_pull_url_map = room_data['stream_url']['hls_pull_url_map']
            flv_pull_url = room_data['stream_url']['flv_pull_url']
            room_data['stream_url']['hls_pull_url_map'] = {**origin_m3u8, **hls_pull_url_map}
            room_data['stream_url']['flv_pull_url'] = {**origin_flv, **flv_pull_url}
            return room_data

        except UnsupportedUrlError:
            unique_id = await self.douyin_utils.get_unique_id(url, proxy_addr=self.proxy_addr)
            return await self.web_stream_fetcher.fetch(f'https://live.douyin.com/{unique_id}', process_data)


class WebStreamDataParser:
    
    def __init__(self, proxy_addr: Optional[str], headers: Dict, stream_orientation: int):
        self.proxy_addr = proxy_addr
        self.headers = headers
        self.stream_orientation = stream_orientation
        self.stream_data_sorter = StreamDataSorter()

    async def parse(self, url: str, process_data: bool = True) -> Dict:
        try:
            url = url.strip()
            html_str = await async_req(url, proxy_addr=self.proxy_addr, headers=self.headers)
            match_json_str = re.search(r'(\{\\"state\\":.*?)]\\n"]\)|\{\\"common\\":.*?)]\\n"]\)</script><div hidden', html_str)
            if not match_json_str:
                raise Exception("Failed to extract JSON string")
            
            json_str = match_json_str.group(1)
            cleaned_string = json_str.replace('\\', '').replace(r'u0026', r'&')
            room_store_match = re.search('"roomStore":(.*?),"linkmicStore"', cleaned_string, re.DOTALL)
            if not room_store_match:
                raise Exception("Failed to extract roomStore")
            
            room_store = room_store_match.group(1)
            anchor_name_match = re.search('"nickname":"(.*?)","avatar_thumb', room_store, re.DOTALL)
            if not anchor_name_match:
                raise Exception("Failed to extract anchor_name")
            anchor_name = anchor_name_match.group(1)
            
            room_store = room_store.split(',"has_commerce_goods"')[0] + '}'*3
            title_match = re.search('"title":"(.*?)","user_count_str"', room_store)
            if not title_match:
                raise Exception("Failed to extract title")
            title_str = title_match.group(1)
            rstr = r"[\/\\\:\\\"\, ]"
            new_title_str = re.sub(rstr, "_", title_str.strip())
            room_store = room_store.replace(title_str, new_title_str)
            
            if not process_data:
                return json.loads(room_store)
            
            json_data = json.loads(room_store)['roomInfo']['room']
            json_data['anchor_name'] = anchor_name
            json_data['live_url'] = url.split('?')[0]
            if json_data.get('status') == 4:
                return json_data
            
            stream_orientation = json_data['stream_url']['stream_orientation']
            match_json_str2 = re.findall(r'"(\{\\"common\\":.*?)"]\)</script><script nonce=', html_str)
            orientation = 2 if stream_orientation == 2 and self.stream_orientation == 2 else 1

            origin_url_list = None
            if match_json_str2 and orientation == 2 and len(match_json_str2) > 1:
                json_str = match_json_str2[1]
                json_str2 = json.loads(
                    json_str.replace('\\', '').replace('"{', '{').replace('}"', '}').replace('u0026', '&'))
                sorted_stream_data = self.stream_data_sorter.sort_streams_by_bitrate(json_str2["data"])
                hls_pull_url_map = {i["name"]: i['hls'] for i in sorted_stream_data}
                flv_pull_url_map = {i["name"]: i['flv'] for i in sorted_stream_data}
                json_data['stream_url']['hls_pull_url_map'] = hls_pull_url_map
                json_data['stream_url']['flv_pull_url'] = flv_pull_url_map
                return json_data
            else:
                if match_json_str2:
                    json_str = match_json_str2[0]
                    json_data2 = json.loads(
                        json_str.replace('\\', '').replace('"{', '{').replace('}"', '}').replace('u0026', '&'))
                    if 'origin' in json_data2['data']:
                        origin_url_list = json_data2['data']['origin']['main']

                if not origin_url_list:
                    html_str = html_str.replace('\\', '').replace('u0026', '&')
                    match_json_str3 = re.search('"origin":\\{"main":(.*?),"dash"', html_str, re.DOTALL)
                    if match_json_str3:
                        origin_url_list = json.loads(match_json_str3.group(1) + '}')

                if origin_url_list:
                    origin_hls_codec = origin_url_list['sdk_params'].get('VCodec') or ''
                    origin_m3u8 = {'ORIGIN': f"{origin_url_list['hls']}&codec={origin_hls_codec}"}
                    origin_flv = {'ORIGIN': f"{origin_url_list['flv']}&codec={origin_hls_codec}"}
                    hls_pull_url_map = json_data['stream_url']['hls_pull_url_map']
                    flv_pull_url = json_data['stream_url']['flv_pull_url']
                    json_data['stream_url']['hls_pull_url_map'] = {**origin_m3u8, **hls_pull_url_map}
                    json_data['stream_url']['flv_pull_url'] = {**origin_flv, **flv_pull_url}

            return json_data
        except Exception as e:
            raise Exception(f"Fetch failed: {url}, {e}")


class StreamUrlBuilder:
    
    def __init__(self, proxy_addr: Optional[str], headers: Dict):
        self.proxy_addr = proxy_addr
        self.headers = headers

    async def build(self, json_data: Dict, video_quality: Optional[str | int] = None) -> StreamData:
        anchor_name = json_data.get('anchor_name')
        live_url = json_data.get('live_url')
        result = {"platform": "抖音", "anchor_name": anchor_name, "is_live": False, "live_url": live_url}
        status = json_data.get("status", 4)
        
        if status == 2:
            stream_url = json_data['stream_url']
            flv_url_dict = stream_url['flv_pull_url']
            flv_url_list: List = list(flv_url_dict.values())
            m3u8_url_dict = stream_url['hls_pull_url_map']
            m3u8_url_list: List = list(m3u8_url_dict.values())
            
            while len(flv_url_list) < 5:
                flv_url_list.append(flv_url_list[-1])
                m3u8_url_list.append(m3u8_url_list[-1])
            
            video_quality, quality_index = self.get_quality_index(video_quality)
            m3u8_url = m3u8_url_list[quality_index]
            flv_url = flv_url_list[quality_index]
            ok = await get_response_status(url=m3u8_url, proxy_addr=self.proxy_addr, headers=self.headers)
            
            if not ok:
                index = quality_index + 1 if quality_index < 4 else quality_index - 1
                m3u8_url = m3u8_url_list[index]
                flv_url = flv_url_list[index]

            result |= {
                'is_live': True,
                'title': json_data.get('title'),
                'quality': video_quality,
                'm3u8_url': m3u8_url,
                'flv_url': flv_url,
                'record_url': m3u8_url or flv_url
            }
        return wrap_stream(result)

    @staticmethod
    def get_quality_index(video_quality: Optional[str | int]) -> tuple:
        return video_quality, 0


class DouyinLiveStream(BaseLiveStream):
    
    def __init__(self, proxy_addr: Optional[str] = None, cookies: Optional[str] = None, stream_orientation: Optional[int] = 1):
        super().__init__(proxy_addr, cookies)
        self.stream_orientation = stream_orientation
        self.pc_headers = self._get_pc_headers()
        self.mobile_headers = self._get_mobile_headers()
        self.web_stream_fetcher = WebStreamDataFetcher(proxy_addr, self.pc_headers, stream_orientation)
        self.app_stream_fetcher = AppStreamDataFetcher(proxy_addr, self.pc_headers, stream_orientation)
        self.web_stream_parser = WebStreamDataParser(proxy_addr, self.pc_headers, stream_orientation)
        self.stream_url_builder = StreamUrlBuilder(proxy_addr, self.pc_headers)

    def _get_pc_headers(self) -> Dict:
        return {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'accept-language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'cookie': self.cookies or '__ac_nonce=064caded4009deafd8b89',
            'referer': 'https://live.douyin.com/'
        }

    def _get_mobile_headers(self) -> Dict:
        return {
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cookie': self.cookies or ''
        }

    async def fetch_app_stream_data(self, url: str, process_data: bool = True) -> Dict:
        return await self.app_stream_fetcher.fetch(url, process_data)

    async def fetch_web_stream_data(self, url: str, process_data: bool = True) -> Dict:
        return await self.web_stream_parser.parse(url, process_data)

    async def fetch_stream_url(self, json_data: Dict, video_quality: Optional[str | int] = None) -> StreamData:
        return await self.stream_url_builder.build(json_data, video_quality)
