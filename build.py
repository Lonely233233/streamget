import PyInstaller.__main__
import os
import sys
import argparse
import platform
import urllib.request
import zipfile
import tarfile
import shutil

class StreamGetPackager:
    def __init__(self):
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        
    def parse_arguments(self):
        parser = argparse.ArgumentParser(description='Package StreamGet tool')
        parser.add_argument('--path', required=True, help='Path to the Python script to package')
        parser.add_argument('--packages', help='Path to site-packages directory (optional)')
        parser.add_argument('--icon', help='Path to icon file (optional)')
        parser.add_argument('--use-upx', action='store_true', help='Use UPX to compress the executable')
        parser.add_argument('--upx-dir', help='Custom path to UPX directory (optional)')
        return parser.parse_args()

    def get_site_packages_path(self):
        try:
            import site
            return site.getsitepackages()[0]
        except:
            python_dir = os.path.dirname(sys.executable)
            return os.path.join(python_dir, 'Lib', 'site-packages')
    
    def download_and_extract_upx(self):
        system = platform.system()
        arch = platform.machine()
        upx_version = "5.0.2"
        upx_dir = "upx_temp"
        
        if os.path.exists(upx_dir):
            shutil.rmtree(upx_dir)
        os.makedirs(upx_dir, exist_ok=True)
        
        try:
            if system == "Windows":
                url = f"https://github.com/upx/upx/releases/download/v{upx_version}/upx-{upx_version}-win64.zip"
                zip_path = os.path.join(upx_dir, "upx.zip")
                urllib.request.urlretrieve(url, zip_path)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(upx_dir)
                os.remove(zip_path)
                
                for root, dirs, files in os.walk(upx_dir):
                    if "upx.exe" in files:
                        return root
            
            elif system == "Linux":
                if "aarch64" in arch or "arm64" in arch:
                    url = f"https://github.com/upx/upx/releases/download/v{upx_version}/upx-{upx_version}-arm64_linux.tar.xz"
                else:
                    url = f"https://github.com/upx/upx/releases/download/v{upx_version}/upx-{upx_version}-amd64_linux.tar.xz"
                
                tar_path = os.path.join(upx_dir, "upx.tar.xz")
                urllib.request.urlretrieve(url, tar_path)
                
                with tarfile.open(tar_path, 'r:xz') as tar_ref:
                    tar_ref.extractall(upx_dir)
                os.remove(tar_path)
                
                for root, dirs, files in os.walk(upx_dir):
                    if "upx" in files:
                        return root
            
            elif system == "Darwin":
                if "arm64" in arch:
                    url = f"https://github.com/upx/upx/releases/download/v{upx_version}/upx-{upx_version}-arm64_macos.tar.xz"
                else:
                    url = f"https://github.com/upx/upx/releases/download/v{upx_version}/upx-{upx_version}-amd64_macos.tar.xz"
                
                tar_path = os.path.join(upx_dir, "upx.tar.xz")
                urllib.request.urlretrieve(url, tar_path)
                
                with tarfile.open(tar_path, 'r:xz') as tar_ref:
                    tar_ref.extractall(upx_dir)
                os.remove(tar_path)
                
                for root, dirs, files in os.walk(upx_dir):
                    if "upx" in files:
                        return root
            
            return upx_dir
        except Exception as e:
            print(f"Error downloading UPX: {e}")
            return None

    def main(self):
        args = self.parse_arguments()
        script_path = os.path.abspath(args.path)
        
        if not os.path.exists(script_path):
            print(f"Error: Script file '{script_path}' does not exist")
            sys.exit(1)
        
        site_packages_path = args.packages or self.get_site_packages_path()
        
        icon_path = None
        if args.icon:
            icon_path = os.path.abspath(args.icon)
            if not os.path.exists(icon_path):
                print(f"Warning: Icon file '{icon_path}' does not exist, ignoring icon")
                icon_path = None
        else:
            default_icon = os.path.join(os.path.dirname(__file__), 'stream.ico')
            if os.path.exists(default_icon):
                icon_path = default_icon
                print(f"Using default icon: {icon_path}")
            else:
                print("No icon file specified and default 'stream.ico' not found")
        
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

        if icon_path:
            pyinstaller_args.append(f'--icon={icon_path}')

        for imp in hidden_imports:
            pyinstaller_args.append(f'--hidden-import={imp}')
        
        upx_dir = None
        if args.use_upx:
            if args.upx_dir:
                upx_dir = os.path.abspath(args.upx_dir)
                if not os.path.exists(os.path.join(upx_dir, "upx")):
                    print(f"Warning: UPX not found in custom directory: {upx_dir}")
                    upx_dir = self.download_and_extract_upx()
            else:
                upx_dir = self.download_and_extract_upx()
            
            if upx_dir:
                pyinstaller_args.append(f'--upx-dir={upx_dir}')
            else:
                print("Warning: UPX compression requested but not available. Continuing without compression.")

        try:
            PyInstaller.__main__.run(pyinstaller_args)
            print("Packaging completed! EXE file is in the ./dist directory")
        except Exception as e:
            print(f"Error during packaging: {e}")
            sys.exit(1)

if __name__ == "__main__":
    packager = StreamGetPackager()
    packager.main()
