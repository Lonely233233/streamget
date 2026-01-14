import asyncio
import argparse
from importlib import import_module
import json
import inspect
import sys
from typing import Dict, Optional, Any, List


class ArgumentParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="Stream URL Fetcher for Multiple Platforms"
        )
        self._setup_arguments()

    def _setup_arguments(self) -> None:
        self.parser.add_argument(
            '-l', '--platform', required=True,
            help='Streaming platform name (e.g., douyin, bilibili)'
        )
        self.parser.add_argument(
            '-i', '--id', required=True,
            help='Room ID or stream identifier'
        )
        self.parser.add_argument(
            '-a', action='store_true',
            help='Additional flag (platform specific)'
        )
        self.parser.add_argument(
            '-p', '--proxy',
            help='Proxy server address (e.g., http://example.com)'
        )

    def parse(self) -> argparse.Namespace:
        args = self.parser.parse_args()
        args.platform = args.platform.lower()
        return args


class PlatformConfig:
    PLATFORMS = {
        'douyin': {'url': 'https://live.douyin.com/{room_id}', 'module': 'DouyinLiveStream'},
        'tiktok': {'url': 'https://www.tiktok.com/{room_id}/live', 'module': 'TikTokLiveStream'},
        'ks': {'url': 'https://live.kuaishou.com/u/{room_id}', 'module': 'KwaiLiveStream'},
        'huya': {'url': 'https://www.huya.com/{room_id}', 'module': 'HuyaLiveStream'},
        'douyu': {'url': 'https://www.douyu.com/{room_id}', 'module': 'DouyuLiveStream'},
        'yy': {'url': 'https://www.yy.com/{room_id}', 'module': 'YYLiveStream'},
        'bilibili': {'url': 'https://live.bilibili.com/{room_id}', 'module': 'BilibiliLiveStream'},
        'xhs': {'url': 'https://www.rednote.com/live/{room_id}', 'module': 'RedNoteLiveStream'},
        'bigo': {'url': 'https://www.bigo.tv/cn/{room_id}', 'module': 'BigoLiveStream'},
        'soop': {'url': 'https://play.sooplive.co.kr/{room_id}', 'module': 'SoopLiveStream'},
        'cc': {'url': 'https://cc.163.com/{room_id}', 'module': 'NeteaseLiveStream'},
        'qiandu': {'url': 'https://qiandurebo.com/web/video.php?roomnumber={room_id}', 'module': 'QiandureboLiveStream'},
        'maoer': {'url': 'https://fm.missevan.com/live/{room_id}', 'module': 'MaoerLiveStream'},
        'look': {'url': 'https://look.163.com/live?id={room_id}', 'module': 'LookLiveStream'},
        'wink': {'url': 'https://www.winktv.co.kr/live/play/{room_id}', 'module': 'WinkTVLiveStream'},
        'flex': {'url': 'https://www.ttinglive.com/channels/{room_id}/live', 'module': 'FlexTVLiveStream'},
        'popkon': {'url': 'https://www.popkontv.com/live/view?castId={room_id}&partnerCode=P-00001', 'module': 'PopkonTVLiveStream'},
        'twitcast': {'url': 'https://twitcasting.tv/{room_id}', 'module': 'TwitCastingLiveStream'},
        'baidu': {'url': 'https://live.baidu.com/m/media/pclive/pchome/live.html?room_id={room_id}', 'module': 'BaiduLiveStream'},
        'weibo': {'url': 'https://weibo.com/l/wblive/p/show/1022:{room_id}', 'module': 'WeiboLiveStream'},
        'kugou': {'url': 'https://fanxing.kugou.com/{room_id}', 'module': 'KugouLiveStream'},
        'twitch': {'url': 'https://www.twitch.tv/{room_id}', 'module': 'TwitchLiveStream'},
        'liveme': {'url': 'https://www.liveme.com/zh/v/{room_id}', 'module': 'LiveMeLiveStream'},
        'huajiao': {'url': 'https://www.huajiao.com/l/{room_id}', 'module': 'HuajiaoLiveStream'},
        'showroom': {'url': 'https://www.showroom-live.com/room/profile?room_id={room_id}', 'module': 'ShowRoomLiveStream'},
        'acfun': {'url': 'https://live.acfun.cn/live/{room_id}', 'module': 'AcfunLiveStream'},
        'inke': {'url': 'https://www.inke.cn/liveroom/index.html?uid=22954469&id={room_id}', 'module': 'InkeLiveStream'},
        'yinbo': {'url': 'https://live.ybw1666.com/{room_id}', 'module': 'YinboLiveStream'},
        'zhihu': {'url': 'https://www.zhihu.com/people/{room_id}', 'module': 'ZhihuLiveStream'},
        'cuzzk': {'url': 'https://chzzk.naver.com/live/{room_id}', 'module': 'ChzzkLiveStream'},
        'haixiu': {'url': 'https://www.haixiutv.com/{room_id}', 'module': 'HaixiuLiveStream'},
        'vvxq': {'url': 'https://h5webcdn-pro.vvxqiu.com//activity/videoShare/videoShare.html?h5Server=https://h5p.vvxqiu.com&roomId={room_id}', 'module': 'VVXQLiveStream'},
        '17live': {'url': 'https://17.live/en/live/{room_id}', 'module': 'YiqiLiveStream'},
        'langlive': {'url': 'https://www.lang.live/en-US/room/{room_id}', 'module': 'LangLiveStream'},
        'piaopiao': {'url': 'https://m.pp.weimipopo.com/live/preview.html?uid=91648673&anchorUid={room_id}', 'module': 'PiaopaioLiveStream'},
        'sixroom': {'url': 'https://v.6.cn/{room_id}', 'module': 'SixRoomLiveStream'},
        'lehai': {'url': 'https://www.lehaitv.com/{room_id}', 'module': 'LehaiLiveStream'},
        'huamao': {'url': 'https://h.catshow168.com/live/preview.html?uid=19066357&anchorUid={room_id}', 'module': 'HuamaoLiveStream'},
        'shopee': {'url': 'https://sg.shp.ee/GmpXeuf?uid=1006401066&session={room_id}', 'module': 'ShopeeLiveStream'},
        'youtube': {'url': 'https://www.youtube.com/watch?v={room_id}', 'module': 'YoutubeLiveStream'},
        'taobao': {'url': 'https://m.tb.cn/{room_id}', 'module': 'TaobaoLiveStream'},
        'jd': {'url': 'https://3.cn/{room_id}', 'module': 'JDLiveStream'},
        'faceit': {'url': 'https://www.faceit.com/zh/players/{room_id}', 'module': 'FaceitLiveStream'},
        'blued': {'url': 'https://app.blued.cn/live?id={room_id}', 'module': 'BluedLiveStream'},
    }

    @classmethod
    def get_config(cls, platform: str) -> Dict[str, str]:
        platform = platform.lower()
        if platform not in cls.PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}")
        return cls.PLATFORMS[platform]

    @classmethod
    def get_url_template(cls, platform: str) -> str:
        return cls.get_config(platform)['url']

    @classmethod
    def get_class_name(cls, platform: str) -> str:
        return cls.get_config(platform)['module']

    @classmethod
    def get_supported_platforms(cls) -> list:
        return list(cls.PLATFORMS.keys())


class PlatformLoader:
    @staticmethod
    def load_class(platform: str):
        class_name = PlatformConfig.get_class_name(platform)
        try:
            module = import_module('streamget')
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Platform module not found: {class_name}"
            ) from e

    @staticmethod
    def create_instance(platform: str, proxy: Optional[str] = None) -> Any:
        cls = PlatformLoader.load_class(platform)
        sig = inspect.signature(cls.__init__)

        params = {}
        if proxy:
            if 'proxy' in sig.parameters:
                params['proxy'] = proxy
            elif 'proxy_addr' in sig.parameters:
                params['proxy_addr'] = proxy
        
        if platform == 'douyin' and 'stream_orientation' in sig.parameters:
            params['stream_orientation'] = 1

        return cls(**params)


class StreamFetcher:
    @staticmethod
    async def fetch(platform: str, room_id: str, proxy: Optional[str] = None) -> str:
        instance = PlatformLoader.create_instance(platform, proxy)
        url_template = PlatformConfig.get_url_template(platform)
        url = url_template.format(room_id=room_id)
        web_data = await instance.fetch_web_stream_data(url)
        stream_obj = await instance.fetch_stream_url(web_data, "OD")
        return stream_obj.to_json()


class OutputFormatter:
    URL_KEYS = ['flv_url', 'm3u8_url', 'record_url', 'rtmp_url']

    @staticmethod
    def format_response(json_data: str, platform: str, room_id: str) -> bytes:
        data = json.loads(json_data)
        urls = []
        seen = set()

        platform_name = data.get("platform", platform)
        
        for key in OutputFormatter.URL_KEYS:
            if key in data and data[key] and data[key] not in seen:
                urls.append({"url": data[key]})
                seen.add(data[key])

        extra = data.get("extra", {})
        if isinstance(extra, dict):
            backup_list = extra.get("backup_url_list", [])
            if isinstance(backup_list, list):
                for url in backup_list:
                    if isinstance(url, str) and url and url not in seen:
                        urls.append({"url": url})
                        seen.add(url)

        return json.dumps({
            "platform": platform_name,
            "rid": room_id,
            "title": data.get("title", ""),
            "anchor": data.get("anchor_name", ""),
            "urls": urls
        }, indent=2, ensure_ascii=False).encode('utf-8')


class ErrorHandler:
    @staticmethod
    def handle(exception: Exception):
        error_msg = f"Error: {str(exception)}\n\nPlease ensure:\n" \
                    "1. You have installed the streamget library (pip install streamget)\n" \
                    "2. Platform name and ID are correct\n" \
                    "3. Proxy server is available (if using -p/--proxy)\n"
        platforms = PlatformConfig.get_supported_platforms()
        error_msg += f"4. Supported platforms: {', '.join(platforms)}"
        sys.stdout.buffer.write(error_msg.encode('utf-8'))
        sys.stdout.buffer.write(b'\n')


class Application:
    @staticmethod
    async def run():
        try:
            args = ArgumentParser().parse()
            json_data = await StreamFetcher.fetch(
                args.platform, args.id, args.proxy
            )
            formatted_bytes = OutputFormatter.format_response(
                json_data, args.platform, args.id
            )
            sys.stdout.buffer.write(formatted_bytes)
            sys.stdout.buffer.write(b'\n')
        except Exception as e:
            ErrorHandler.handle(e)


if __name__ == "__main__":
    asyncio.run(Application.run())
