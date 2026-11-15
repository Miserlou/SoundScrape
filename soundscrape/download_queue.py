"""Bounded concurrent downloads, with UI-independent job events."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import queue
import threading
import time
import uuid

from soundscrape.downloader import download, validate_url


class DownloadQueue:
    def __init__(self, workers=3, downloader=download):
        self.events = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="download")
        self.downloader = downloader
        self.lock = threading.Lock()
        self.active = set()

    def submit(self, url, destination):
        url = validate_url(url)
        destination = str(Path(destination).expanduser().resolve())
        key = (url, str(Path(destination)).casefold())
        job_id = uuid.uuid4().hex
        with self.lock:
            if key in self.active:
                return None
            self.active.add(key)
        try:
            self.executor.submit(self.worker, job_id, key, url, destination)
        except Exception:
            with self.lock:
                self.active.remove(key)
            raise
        return job_id

    def worker(self, job_id, key, url, destination):
        events = self.events
        events.put((job_id, "started", None))
        last_update = 0

        def progress(data):
            nonlocal last_update
            now = time.monotonic()
            if data["status"] == "finished" or now - last_update >= 0.15:
                last_update = now
                snapshot = {name: data.get(name) for name in
                            ("status", "downloaded_bytes", "total_bytes", "total_bytes_estimate")}
                events.put((job_id, "progress", snapshot))

        class Logger:
            def debug(self, message):
                pass

            def warning(self, message):
                events.put((job_id, "log", message))

            def error(self, message):
                events.put((job_id, "log", message))

        kind, result = "done", "다운로드 완료"
        try:
            self.downloader(url, destination, progress, Logger())
        except Exception as exc:
            kind, result = "error", str(exc)
        finally:
            with self.lock:
                self.active.remove(key)
        events.put((job_id, kind, result))

    def shutdown(self):
        self.executor.shutdown(wait=False)
