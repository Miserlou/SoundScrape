"""Windowed entry point. No legacy CLI dependencies are imported."""

import os
from pathlib import Path
import queue
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from soundscrape.downloader import validate_url
from soundscrape.download_queue import DownloadQueue


class App:
    def __init__(self, root):
        self.root = root
        root.iconbitmap(default=str(Path(__file__).resolve().parent / "assets" / "soundscrape.ico"))
        self.downloads = DownloadQueue(workers=3)
        self.jobs = {}
        root.title("SoundScrape")
        root.geometry("900x650")
        root.minsize(700, 560)
        root.protocol("WM_DELETE_WINDOW", self.close)
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="SoundScrape", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(frame, text="링크를 한 줄에 하나씩 입력하세요. 최대 3개를 동시에 다운로드합니다.").pack(anchor="w", pady=(4, 16))
        self.destination = tk.StringVar(value=str(Path.home() / "Downloads" / "SoundScrape"))
        ttk.Label(frame, text="트랙 / 믹스 링크").pack(anchor="w")
        self.entry = tk.Text(frame, height=3, wrap="none")
        self.entry.pack(fill="x", pady=(5, 12))
        self.entry.focus_set()
        ttk.Label(frame, text="저장 위치").pack(anchor="w")
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(5, 16))
        self.folder = ttk.Entry(row, textvariable=self.destination)
        self.folder.pack(side="left", fill="x", expand=True)
        self.choose = ttk.Button(row, text="변경", command=self.choose_folder)
        self.choose.pack(side="left", padx=(8, 0))
        self.start_button = ttk.Button(frame, text="다운로드 추가", command=self.start)
        self.start_button.pack(fill="x")
        self.status = tk.StringVar(value="준비됨 · 진행 중에도 링크를 추가할 수 있습니다.")
        listing = ttk.Frame(frame)
        listing.pack(fill="both", expand=True, pady=(16, 8))
        self.tasks = ttk.Treeview(listing, columns=("url", "status", "progress"), show="headings", height=7)
        for column, label, width in (("url", "링크", 480), ("status", "상태", 100), ("progress", "진행률", 100)):
            self.tasks.heading(column, text=label)
            self.tasks.column(column, width=width, minwidth=80, stretch=column == "url")
        scroll = ttk.Scrollbar(listing, orient="vertical", command=self.tasks.yview)
        self.tasks.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tasks.pack(side="left", fill="both", expand=True)
        ttk.Label(frame, textvariable=self.status, wraplength=620).pack(anchor="w")
        self.log = tk.Text(frame, height=4, wrap="word", state="disabled")
        self.log.pack(fill="x", pady=(10, 8))
        ttk.Button(frame, text="저장 폴더 열기", command=self.open_folder).pack(anchor="e")
        root.after(100, self.poll)

    def choose_folder(self):
        chosen = filedialog.askdirectory(initialdir=str(Path.home()))
        if chosen:
            self.destination.set(chosen)

    def open_folder(self):
        try:
            selection = self.tasks.selection()
            path = Path(self.jobs[selection[0]]["destination"] if selection else self.destination.get()).expanduser()
            path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(path.resolve()))
        except OSError as exc:
            messagebox.showerror("폴더 열기 실패", str(exc))

    def start(self):
        try:
            urls = [validate_url(line) for line in self.entry.get("1.0", "end").splitlines() if line.strip()]
            if not urls:
                raise ValueError("다운로드할 링크를 입력해 주세요.")
            if not self.destination.get().strip():
                raise ValueError("저장 위치를 선택해 주세요.")
            destination = str(Path(self.destination.get()).expanduser().resolve())
        except ValueError as exc:
            messagebox.showerror("입력 확인", str(exc))
            return
        for url in urls:
            job_id = self.downloads.submit(url, destination)
            if job_id is None:
                self.append_log(f"이미 대기 또는 다운로드 중인 링크입니다: {url}")
                continue
            self.jobs[job_id] = {"url": url, "destination": destination, "state": "queued"}
            self.tasks.insert("", "end", iid=job_id, values=(url, "대기 중", "—"))
            self.tasks.see(job_id)
        self.entry.delete("1.0", "end")
        self.update_summary()

    def append_log(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def update_summary(self):
        counts = {state: sum(job["state"] == state for job in self.jobs.values())
                  for state in ("queued", "running", "done", "error")}
        self.status.set(f"다운로드 중 {counts['running']} · 대기 {counts['queued']} · 완료 {counts['done']} · 실패 {counts['error']}")

    def poll(self):
        try:
            for _ in range(200):
                job_id, kind, value = self.downloads.events.get_nowait()
                job = self.jobs[job_id]
                if kind == "started":
                    job["state"] = "running"
                    self.tasks.set(job_id, "status", "링크 확인 중")
                elif kind == "progress":
                    total = value.get("total_bytes") or value.get("total_bytes_estimate")
                    if value["status"] == "downloading":
                        if total:
                            percent = min(100, (value.get("downloaded_bytes") or 0) * 100 / total)
                            self.tasks.set(job_id, "progress", f"{percent:.1f}%")
                        else:
                            self.tasks.set(job_id, "progress", f"{(value.get('downloaded_bytes') or 0) / 1048576:.1f} MB")
                        self.tasks.set(job_id, "status", "다운로드 중")
                    elif value["status"] == "finished":
                        self.tasks.set(job_id, "status", "파일 마무리 중")
                elif kind == "log":
                    self.append_log(f"[{job['url']}] {value}")
                elif kind in ("done", "error"):
                    job["state"] = kind
                    self.tasks.set(job_id, "status", "완료" if kind == "done" else "실패")
                    if kind == "done":
                        self.tasks.set(job_id, "progress", "100%")
                    if kind == "error":
                        self.append_log(f"[{job['url']}] {value}")
        except queue.Empty:
            pass
        self.update_summary()
        self.root.after(100, self.poll)

    def close(self):
        if any(job["state"] in ("queued", "running") for job in self.jobs.values()):
            messagebox.showinfo("다운로드 진행 중", "대기 및 진행 중인 다운로드가 끝난 뒤 창을 닫아 주세요.")
            return
        self.downloads.shutdown()
        self.root.destroy()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--smoke-test":
        from soundscrape.smoke import main
        raise SystemExit(main(sys.argv[2:]))
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SoundScrape.Desktop")
    window = tk.Tk()
    if "--check-runtime" in sys.argv:
        window.withdraw()
        app = App(window)
        window.update()
        app.close()
        raise SystemExit(0)
    App(window)
    window.mainloop()
