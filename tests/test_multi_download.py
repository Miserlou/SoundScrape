import queue
import tempfile
import threading
import unittest

from soundscrape.download_queue import DownloadQueue


class ConcurrentDownloadTests(unittest.TestCase):
    def test_limit_add_during_download_and_independent_failure(self):
        condition = threading.Condition()
        started = set()
        release = [threading.Event() for _ in range(4)]

        def downloader(url, destination, progress, logger):
            index = int(url.rsplit("/", 1)[1])
            with condition:
                started.add(index)
                condition.notify_all()
            if not release[index].wait(5):
                raise RuntimeError("test download timed out")
            progress({"status": "downloading", "downloaded_bytes": index + 1, "total_bytes": 10})
            if index == 0:
                raise RuntimeError("one track failed")

        downloads = DownloadQueue(workers=3, downloader=downloader)
        try:
            with tempfile.TemporaryDirectory() as destination:
                ids = [downloads.submit(f"https://soundcloud.com/test/{i}", destination) for i in range(3)]
                with condition:
                    self.assertTrue(condition.wait_for(lambda: len(started) == 3, timeout=3))
                # Adding a fourth job while three are blocked must remain queued.
                ids.append(downloads.submit("https://soundcloud.com/test/3", destination))
                self.assertEqual(started, {0, 1, 2})
                release[0].set()
                with condition:
                    self.assertTrue(condition.wait_for(lambda: 3 in started, timeout=3))
                for event in release:
                    event.set()
                downloads.executor.shutdown(wait=True)
                events = []
                while not downloads.events.empty():
                    events.append(downloads.events.get_nowait())
                terminal = {job_id: (kind, value) for job_id, kind, value in events if kind in ("done", "error")}
                self.assertEqual(terminal[ids[0]], ("error", "one track failed"))
                self.assertTrue(all(terminal[job_id][0] == "done" for job_id in ids[1:]))
                for index, job_id in enumerate(ids):
                    progress = [value for event_id, kind, value in events if event_id == job_id and kind == "progress"]
                    self.assertEqual(progress[0]["downloaded_bytes"], index + 1)
        finally:
            for event in release:
                event.set()
            downloads.executor.shutdown(wait=True)

    def test_duplicate_does_not_start_twice_and_can_retry_after_failure(self):
        release = threading.Event()

        def downloader(*args):
            release.wait(3)
            raise RuntimeError("unavailable")

        downloads = DownloadQueue(downloader=downloader)
        try:
            with tempfile.TemporaryDirectory() as destination:
                url = "https://www.mixcloud.com/test/mix/"
                first = downloads.submit(url, destination)
                self.assertIsNone(downloads.submit(url, destination))
                release.set()
                while True:
                    job_id, kind, value = downloads.events.get(timeout=3)
                    if job_id == first and kind == "error":
                        break
                self.assertIsNotNone(downloads.submit(url, destination))
        finally:
            release.set()
            downloads.executor.shutdown(wait=True)

    def test_invalid_link_never_enters_queue(self):
        downloads = DownloadQueue()
        try:
            with self.assertRaises(ValueError):
                downloads.submit("https://example.com/audio", ".")
            with self.assertRaises(queue.Empty):
                downloads.events.get_nowait()
            self.assertFalse(downloads.active)
        finally:
            downloads.shutdown()


if __name__ == "__main__":
    unittest.main()
