# Desktop distribution

SoundScrape's source is distributed under the MIT license in LICENSE.
The desktop executable also contains third-party software with its own terms:

- Python and Tcl/Tk: https://docs.python.org/3/license.html and https://www.tcl.tk/software/tcltk/license.html
- yt-dlp: https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE
- curl_cffi, curl-impersonate, and curl: https://github.com/lexiforest/curl_cffi/blob/main/LICENSE
- imageio-ffmpeg: https://github.com/imageio/imageio-ffmpeg/blob/main/LICENSE
- FFmpeg bundled by imageio-ffmpeg: https://ffmpeg.org/legal.html
- certifi: https://github.com/certifi/python-certifi/blob/master/LICENSE
- Node.js (including its third-party notices): https://github.com/nodejs/node/blob/main/LICENSE
- yt-dlp-ejs: https://github.com/yt-dlp/ejs/blob/main/LICENSE
- PyInstaller bootloader (GPL with distribution exception): https://pyinstaller.org/en/stable/license.html

FFmpeg build configuration and license information are available by running the
bundled binary with `-version` and `-L` in the development environment. Before
publishing a public binary, include the licenses and corresponding source/build
information required by the actual FFmpeg build being distributed. This notice
alone does not replace those requirements.
