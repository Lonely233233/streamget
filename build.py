import PyInstaller.__main__
import os
import sys
import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description='打包 StreamGet 工具')
    parser.add_argument('--path', required=True, help='要打包的 Python 脚本路径')
    parser.add_argument('--packages', help='site-packages 目录路径（可选）')
    return parser.parse_args()

def get_site_packages_path():
    try:
        import site
        return site.getsitepackages()[0]
    except:
        python_dir = os.path.dirname(sys.executable)
        return os.path.join(python_dir, 'Lib', 'site-packages')

def main():
    args = parse_arguments()
    script_path = os.path.abspath(args.path)
    
    if not os.path.exists(script_path):
        print(f"错误: 脚本文件 '{script_path}' 不存在")
        sys.exit(1)
    
    site_packages_path = args.packages or get_site_packages_path()
    
    hidden_imports = [
        'streamget',
        'PyExecJS',
        'distro',
        'httpx',
        'h2',
        'loguru',
        'pycryptodome',
        'requests',
        'tqdm',
        'asyncio',
        'argparse',
        'json',
        'inspect',
        'typing',
        'importlib',
        'streamget.DouyinLiveStream',
        'streamget.TikTokLiveStream',
        'streamget.KwaiLiveStream',
        'streamget.HuyaLiveStream',
        'streamget.DouyuLiveStream',
        'streamget.YYLiveStream',
        'streamget.BilibiliLiveStream',
        'streamget.RedNoteLiveStream',
        'streamget.BigoLiveStream',
        'streamget.SoopLiveStream',
        'streamget.NeteaseLiveStream',
        'streamget.QiandureboLiveStream',
        'streamget.MaoerLiveStream',
        'streamget.LookLiveStream',
        'streamget.WinkTVLiveStream',
        'streamget.FlexTVLiveStream',
        'streamget.PopkonTVLiveStream',
        'streamget.TwitCastingLiveStream',
        'streamget.BaiduLiveStream',
        'streamget.WeiboLiveStream',
        'streamget.KugouLiveStream',
        'streamget.TwitchLiveStream',
        'streamget.LiveMeLiveStream',
        'streamget.HuajiaoLiveStream',
        'streamget.ShowRoomLiveStream',
        'streamget.AcfunLiveStream',
        'streamget.InkeLiveStream',
        'streamget.YinboLiveStream',
        'streamget.ZhihuLiveStream',
        'streamget.ChzzkLiveStream',
        'streamget.HaixiuLiveStream',
        'streamget.VVXQLiveStream',
        'streamget.YiqiLiveStream',
        'streamget.LangLiveLiveStream',
        'streamget.PiaopaioLiveStream',
        'streamget.SixRoomLiveStream',
        'streamget.LehaiLiveStream',
        'extremely.HuamaoLiveStream',
        'streamget.ShopeeLiveStream',
        'streamget.YoutubeLiveStream',
        'streamget.TaobaoLiveStream',
        'streamget.JDLiveStream',
        'streamget.FaceitLiveStream',
        'streamget.BluedLiveStream',
    ]

    pyinstaller_args = [
        script_path,
        '--name=streamget',
        '--onefile',
        '--console',
        '--clean',
        '--distpath=./dist',
        '--workpath=./build',
        f'--paths={site_packages_path}'
    ]

    for imp in hidden_imports:
        pyinstaller_args.append(f'--hidden-import={imp}')

    print(f"开始打包脚本: {script_path}")
    print(f"使用 site-packages 路径: {site_packages_path}")
    
    PyInstaller.__main__.run(pyinstaller_args)

    print("打包完成！EXE 文件位于 ./dist 目录中")

if __name__ == "__main__":
    main()