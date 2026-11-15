"""Windowed entry point. No legacy CLI dependencies are imported."""

import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from soundscrape.downloader import download, validate_url


class App:
    def __init__(self, root):
        self.root = root
        self.events = queue.Queue()
        self.busy = False
        root.title("SoundScrape")
        root.geometry("700x460")
        root.minsize(580, 400)
        root.protocol("WM_DELETE_WINDOW", self.close)
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="SoundScrape", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(frame, text="SoundCloud · Mixcloud 링크를 붙여넣고 다운로드하세요.").pack(anchor="w", pady=(4, 20))
        self.url = tk.StringVar()
        self.destination = tk.StringVar(value=str(Path.home() / "Downloads" / "SoundScrape"))
        ttk.Label(frame, text="트랙 / 믹스 링크").pack(anchor="w")
        self.entry = ttk.Entry(frame, textvariable=self.url)
        self.entry.pack(fill="x", pady=(5, 12))
        self.entry.focus_set()
        ttk.Label(frame, text="저장 위치").pack(anchor="w")
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(5, 16))
        self.folder = ttk.Entry(row, textvariable=self.destination)
        self.folder.pack(side="left", fill="x", expand=True)
        self.choose = ttk.Button(row, text="변경", command=self.choose_folder)
        self.choose.pack(side="left", padx=(8, 0))
        self.start_button = ttk.Button(frame, text="다운로드", command=self.start)
        self.start_button.pack(fill="x")
        self.bar = ttk.Progressbar(frame, maximum=100)
        self.bar.pack(fill="x", pady=(16, 8))
        self.status = tk.StringVar(value="준비됨 · 원본 오디오 형식으로 저장합니다.")
        ttk.Label(frame, textvariable=self.status, wraplength=620).pack(anchor="w")
        self.log = tk.Text(frame, height=5, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, pady=(10, 8))
        ttk.Button(frame, text="저장 폴더 열기", command=self.open_folder).pack(anchor="e")
        root.after(100, self.poll)

    def choose_folder(self):
        chosen = filedialog.askdirectory(initialdir=str(Path.home()))
        if chosen:
            self.destination.set(chosen)

    def open_folder(self):
        try:
            path = Path(self.destination.get()).expanduser()
            path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(path.resolve()))
        except OSError as exc:
            messagebox.showerror("폴더 열기 실패", str(exc))

    def start(self):
        if self.busy:
            return
        try:
            url = validate_url(self.url.get())
            if not self.destination.get().strip():
                raise ValueError("저장 위치를 선택해 주세요.")
            destination = str(Path(self.destination.get()).expanduser().resolve())
        except ValueError as exc:
            messagebox.showerror("입력 확인", str(exc))
            return
        self.busy = True
        for widget in (self.entry, self.folder, self.choose, self.start_button):
            widget.configure(state="disabled")
        self.bar.configure(mode="indeterminate")
        self.bar.start()
        self.status.set("링크 확인 중…")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        threading.Thread(target=self.worker, args=(url, destination), daemon=True).start()

    def worker(self, url, destination):
        app = self

        class Logger:
            def debug(self, message):
                pass

            def warning(self, message):
                app.events.put(("log", message))

            def error(self, message):
                app.events.put(("log", message))

        try:
            download(url, destination, lambda data: self.events.put(("progress", data)), Logger())
            self.events.put(("done", "다운로드 완료 · 저장 폴더에서 확인하세요."))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    total = value.get("total_bytes") or value.get("total_bytes_estimate")
                    if value["status"] == "downloading":
                        if total:
                            self.bar.stop()
                            percent = min(100, value.get("downloaded_bytes", 0) * 100 / total)
                            self.bar.configure(mode="determinate", value=percent)
                            self.status.set(f"다운로드 중… {percent:.1f}%")
                        else:
                            self.status.set(f"다운로드 중… {value.get('downloaded_bytes', 0) / 1048576:.1f} MB")
                    elif value["status"] == "finished":
                        self.status.set("파일 마무리 중…")
                elif kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", str(value) + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                else:
                    self.busy = False
                    self.bar.stop()
                    self.bar.configure(mode="determinate", value=100 if kind == "done" else 0)
                    for widget in (self.entry, self.folder, self.choose, self.start_button):
                        widget.configure(state="normal")
                    self.status.set(value if kind == "done" else "다운로드 실패 · 링크와 아래 오류를 확인해 주세요.")
                    if kind == "error":
                        self.log.configure(state="normal")
                        self.log.insert("end", value + "\n")
                        self.log.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo("다운로드 진행 중", "다운로드가 끝난 뒤 창을 닫아 주세요.")
            return
        self.root.destroy()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--smoke-test":
        from soundscrape.smoke import main
        raise SystemExit(main(sys.argv[2:]))
    window = tk.Tk()
    if "--check-runtime" in sys.argv:
        window.withdraw()
        App(window)
        window.update()
        window.destroy()
        raise SystemExit(0)
    App(window)
    window.mainloop()
