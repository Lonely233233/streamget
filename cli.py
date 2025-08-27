import asyncio
import argparse
from importlib import import_module
import json
import inspect
from typing import Dict, Optional


class ArgumentParser:
        def __init__(self):
                self.parser = argparse.ArgumentParser()
                self._setup_arguments()

        def _setup_arguments(self) -> None:
                self.parser.add_argument('-l', '--platform', required=True, help='Streaming platform name')
                self.parser.add_argument('-i', '--id', required=True, help='Room ID')
                self.parser.add_argument('-a', action='store_true', help='Additional flag')
                self.parser.add_argument('-p', '--proxy', help='Proxy server address')

        def parse(self) -> argparse.Namespace:
                args = self.parser.parse_args()
                args.platform = args.platform.lower()
                return args


class PlatformConfig:
        def __init__(self):
                self._platforms: Dict[str, Dict[str, str]] = {
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

        def get_url_template(self, platform: str) -> str:
                platform = platform.lower()
                config = self._platforms.get(platform)
                if not config:
                        raise ValueError(f"平台 {platform} 未配置")
                return config['url']

        def get_class_name(self, platform: str) -> str:
                platform = platform.lower()
                config = self._platforms.get(platform)
                return config['module'] if config else f"{platform.capitalize()}LiveStream"

        def get_supported_platforms(self) -> list:
                return list(self._platforms.keys())


class PlatformClassLoader:
        def __init__(self, config: PlatformConfig):
                self._config = config

        def load(self, platform: str, proxy: Optional[str] = None):
                class_name = self._config.get_class_name(platform)
                try:
                        module = import_module('streamget')
                        class_obj = getattr(module, class_name)
                        return self._create_instance(class_obj, proxy)
                except (ImportError, AttributeError) as e:
                        raise ImportError(f"不支持的平台: {platform}") from e

        def _create_instance(self, class_obj, proxy: Optional[str]):
                sig = inspect.signature(class_obj.__init__)
                params = {}
                if proxy and ('proxy_addr' in sig.parameters or 'proxy' in sig.parameters):
                        param_name = 'proxy_addr' if 'proxy_addr' in sig.parameters else 'proxy'
                        params[param_name] = proxy
                return class_obj(**params)

class StreamFetcher:
        def __init__(self, class_loader: PlatformClassLoader, config: PlatformConfig):
                self._class_loader = class_loader
                self._config = config

        async def fetch(self, platform: str, room_id: str, proxy: Optional[str] = None) -> str:
                platform = platform.lower()
                live_stream = self._class_loader.load(platform, proxy)
                url = self._config.get_url_template(platform).format(room_id=room_id)
                web_data = await live_stream.fetch_web_stream_data(url)
                stream_obj = await live_stream.fetch_stream_url(web_data)
                return stream_obj.to_json()


class OutputFormatter:
        def format(self, json_data: str, platform: str, room_id: str) -> str:
                data = json.loads(json_data)
                formatted_data = {
                        "platform": data.get("platform", platform.lower()),
                        "rid": room_id,
                        "title": data.get("title"),
                        "anchor": data.get("anchor_name"),
                        "urls": [
                                {"url": url_value}
                                for url_type in ['m3u8_url', 'flv_url', 'record_url', 'rtmp_url']
                                if (url_value := data.get(url_type))
                        ]
                }
                return json.dumps(formatted_data, indent=2, ensure_ascii=True)


class ErrorHandler:
        def __init__(self, config: PlatformConfig):
                self._config = config

        def handle(self, exception: Exception) -> None:
                print(f"错误: {str(exception)}")
                print("请确保:")
                print("1. 已安装 streamget 库 (pip install streamget)")
                print("2. 平台名称和 ID 正确")
                print("3. 代理服务器可用 (如果使用 -p/--proxy)")
                print(f"4. 支持的平台: {', '.join(self._config.get_supported_platforms())}")


class StreamGetTool:
        def __init__(self):
                self._config = PlatformConfig()
                self._class_loader = PlatformClassLoader(self._config)
                self._stream_fetcher = StreamFetcher(self._class_loader, self._config)
                self._formatter = OutputFormatter()
                self._error_handler = ErrorHandler(self._config)
                self._args = ArgumentParser().parse()

        async def run(self) -> None:
                try:
                        json_data = await self._stream_fetcher.fetch(
                                self._args.platform, self._args.id, self._args.proxy
                        )
                        formatted = self._formatter.format(json_data, self._args.platform, self._args.id)
                        print(formatted)
                except Exception as e:
                        self._error_handler.handle(e)


def main():
        asyncio.run(StreamGetTool().run())


if __name__ == "__main__":
        main()