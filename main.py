from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import yt_dlp
import os
from pathlib import Path
import re

app = FastAPI()

# 设置静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 确保下载目录存在
DOWNLOAD_DIR = Path("static/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

def is_valid_youtube_url(url: str) -> bool:
    # YouTube URL 验证模式
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    match = re.match(youtube_regex, url)
    return bool(match)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/download", response_class=HTMLResponse)
async def download_video(request: Request, url: str = Form(...), audio_format: str = Form('m4a')):
    try:
        # 验证 YouTube URL
        if not is_valid_youtube_url(url):
            raise ValueError("无效的YouTube链接，请确保链接完整且正确")

        # 验证音频格式
        if audio_format not in ['m4a', 'mp3']:
            audio_format = 'm4a'

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(DOWNLOAD_DIR / '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': '192',
            }],
            'prefer_ffmpeg': True,
            'keepvideo': True,
            'extract_flat': False,
            'quiet': False,
            'no_warnings': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            'socket_timeout': 30,
            'retries': 3,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"开始处理URL: {url}")  # 调试信息
            
            try:
                # 先获取信息而不下载
                info_dict = ydl.extract_info(url, download=False)
                if not info_dict:
                    raise ValueError("无法获取视频信息")
                
                # 处理视频标题
                video_title = info_dict.get('title', None)
                if not video_title:
                    video_title = 'video'
                    
                # 清理视频标题
                video_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()
                if not video_title:
                    video_title = 'video'
                
                print(f"视频标题: {video_title}")  # 调试信息
                
                # 设置具体的输出路径
                ydl_opts['outtmpl'] = str(DOWNLOAD_DIR / f'{video_title}.%(ext)s')
                
                # 使用新的配置下载
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                    download_info = ydl_download.download([url])
                
                # 获取视频时长
                duration = info_dict.get('duration')
                if not isinstance(duration, (int, float)):
                    duration = 0
                
                # 构建视频信息
                video_info = {
                    'title': video_title,
                    'duration': str(int(duration)),
                    'video_path': f"/static/downloads/{video_title}.mp4",
                    'audio_path': f"/static/downloads/{video_title}.{audio_format}",
                    'thumbnail': info_dict.get('thumbnail'),
                    'filesize': f"{int(info_dict.get('filesize', 0) / 1024 / 1024)}MB" if info_dict.get('filesize') else None
                }
                print(f"下载完成: {video_info}")  # 调试信息
                
                return templates.TemplateResponse(
                    "index.html", 
                    {"request": request, "video_info": video_info}
                )
                
            except Exception as e:
                print(f"处理视频时出错: {str(e)}")
                raise ValueError(f"处理视频时出错: {str(e)}")
    
    except Exception as e:
        error_message = f"下载出错: {str(e)}"
        print(error_message)  # 控制台输出错误信息
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "error": error_message}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 