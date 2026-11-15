"""Shared download path for the desktop app and live smoke tests."""

from pathlib import Path
import re
import shutil
import sys
from urllib.parse import parse_qs, urlsplit

import imageio_ffmpeg
from yt_dlp import YoutubeDL


def validate_url(value):
    value = value.strip()
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    platforms = ("soundcloud.com", "mixcloud.com", "youtube.com", "youtu.be")
    if (parsed.scheme not in ("http", "https")
            or parsed.username or parsed.password
            or not any(host == site or host.endswith("." + site) for site in platforms)
            or not parsed.path.strip("/")):
        raise ValueError("SoundCloud, Mixcloud 또는 YouTube 링크를 입력해 주세요.")
    if is_youtube(value):
        parts = parsed.path.strip("/").split("/")
        video_id = (parts[0] if host in ("youtu.be", "www.youtu.be") else
                    parse_qs(parsed.query).get("v", [""])[0] if parts[0] == "watch" else
                    parts[1] if len(parts) == 2 and parts[0] in ("shorts", "live", "embed") else "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("YouTube 영상 링크를 입력해 주세요. 채널·재생목록 전체 다운로드는 지원하지 않습니다.")
    return value


def is_youtube(url):
    host = (urlsplit(url).hostname or "").lower()
    return host == "youtu.be" or host.endswith(".youtu.be") or host == "youtube.com" or host.endswith(".youtube.com")


def node_runtime():
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    bundled = root / "runtime" / "node.exe"
    if bundled.is_file():
        return str(bundled)
    if not getattr(sys, "frozen", False):
        installed = shutil.which("node")
        if installed:
            return installed
    raise RuntimeError("YouTube 오디오 처리에 필요한 실행 파일이 없습니다. 최신 SoundScrape EXE를 다시 다운로드해 주세요.")


def download(url, destination, progress=None, logger=None):
    url = validate_url(url)
    destination = Path(destination).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    options = {
        "format": "bestaudio",
        "paths": {"home": str(destination)},
        "outtmpl": "%(uploader)s - %(title)s [%(id)s].%(ext)s",
        "windowsfilenames": True,
        "trim_file_name": 180,
        "noplaylist": True,
        "overwrites": False,
        "continuedl": True,
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "skip_unavailable_fragments": False,
        "quiet": True,
        "noprogress": True,
        "cachedir": False,
        # Keep redirects/unsupported links away from generic site extractors.
        "allowed_extractors": ["soundcloud.*", "mixcloud.*", "youtube.*"],
    }
    if is_youtube(url):
        options["js_runtimes"] = {"node": {"path": node_runtime()}}
    if progress:
        options["progress_hooks"] = [progress]
    if logger:
        options["logger"] = logger
    with YoutubeDL(options) as client:
        result = client.extract_info(url, download=True)
    if not result:
        raise RuntimeError("다운로드 결과가 없습니다.")
    return result
