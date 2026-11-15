"""Shared download path for the desktop app and live smoke tests."""

from pathlib import Path
from urllib.parse import urlsplit

import imageio_ffmpeg
from yt_dlp import YoutubeDL


def validate_url(value):
    value = value.strip()
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    platforms = ("soundcloud.com", "mixcloud.com")
    if (parsed.scheme not in ("http", "https")
            or parsed.username or parsed.password
            or not any(host == site or host.endswith("." + site) for site in platforms)
            or not parsed.path.strip("/")):
        raise ValueError("SoundCloud 또는 Mixcloud의 트랙·믹스 링크를 입력해 주세요.")
    return value


def download(url, destination, progress=None, logger=None):
    url = validate_url(url)
    destination = Path(destination).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    options = {
        "format": "bestaudio/best",
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
        "allowed_extractors": ["soundcloud.*", "mixcloud.*"],
    }
    if progress:
        options["progress_hooks"] = [progress]
    if logger:
        options["logger"] = logger
    with YoutubeDL(options) as client:
        result = client.extract_info(url, download=True)
    if not result:
        raise RuntimeError("다운로드 결과가 없습니다.")
    return result
