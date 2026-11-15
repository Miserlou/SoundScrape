"""Download a real track and check that its saved audio decodes."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import traceback

import imageio_ffmpeg
from yt_dlp.version import __version__ as engine_version

from soundscrape.downloader import download


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    report = {"url": args.url, "engine": engine_version, "success": False}
    try:
        finished = []

        def progress(data):
            if data["status"] == "finished":
                finished.append(data["filename"])

        info = download(args.url, args.output, progress)
        if not finished:
            raise RuntimeError("No downloaded audio file was reported; use a fresh output folder.")
        files = []
        for name in dict.fromkeys(finished):
            path = Path(name)
            if not path.is_file() or path.stat().st_size < 1024:
                raise RuntimeError(f"Missing or empty audio: {path}")
            # The entire file is downloaded; decode the first 15 seconds to
            # distinguish playable audio from an HTML error/manifest response.
            command = [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-nostdin",
                       "-i", str(path), "-t", "15", "-map", "0:a:0", "-f", "null", "-"]
            result = subprocess.run(command, capture_output=True, text=True, timeout=90,
                                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            if result.returncode or result.stderr.strip():
                raise RuntimeError(f"Audio decode failed: {result.stderr}")
            files.append({"name": path.name, "bytes": path.stat().st_size, "decode_seconds": 15})
        report.update(success=True, title=info.get("title"), duration=info.get("duration"), files=files)
    except Exception:
        report["error"] = traceback.format_exc()
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
