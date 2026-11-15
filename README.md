# SoundScrape Desktop — Windows

SoundCloud 또는 Mixcloud 링크를 붙여넣어 오디오를 저장하는 Windows 앱입니다.
기존 Python CLI는 아래에 보존되어 있으며, 데스크톱 앱은 별도의 최신 다운로드
엔진을 사용합니다.

## 사용하기

1. 이 저장소의 **Releases**에서 `SoundScrape.exe`를 다운로드합니다.
2. EXE를 실행하고 SoundCloud 트랙 또는 Mixcloud 믹스 링크를 붙여넣습니다.
3. **다운로드**를 누릅니다. 기본 저장 위치는 `Downloads/SoundScrape`입니다.
4. 완료 후 **저장 폴더 열기**로 파일을 확인합니다.

여러 링크를 한 줄에 하나씩 입력하고 **다운로드 추가**를 누를 수 있습니다.
최대 3개가 동시에 다운로드되며 나머지는 대기열에서 순서대로 시작합니다.
진행 중에도 링크를 계속 추가할 수 있고, 각 항목의 진행률·완료·실패를 따로 확인합니다.
저장 위치를 바꾸면 새로 추가하는 항목부터 적용됩니다. 목록에서 항목을 선택한 뒤
**저장 폴더 열기**를 누르면 그 항목의 저장 위치가 열립니다.

Python, FFmpeg 설치나 터미널 입력은 필요하지 않습니다. 오디오는 제공되는
최상위 음질의 원래 형식으로 저장하며, MP3 변환은 하지 않습니다.
공개 트랙과 믹스가 우선 검증 대상입니다. 로그인·구독·지역 제한이 있는 링크는
서버 정책에 따라 실패할 수 있으며 앱에 오류가 표시됩니다.

## 개발 및 Windows 빌드

Python 3.13 64비트와 Tkinter를 사용할 수 있는 Windows에서:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python.exe desktop.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_desktop.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_multi_download.py -v
powershell -NoProfile -ExecutionPolicy Bypass -File .\build-windows.ps1
```

결과는 `dist/SoundScrape.exe` 및 SHA-256 체크섬입니다. 기존 `requirements.txt`는
구형 CLI 전용이므로 데스크톱 빌드에서는 설치하지 않습니다.

EXE 파일·창·작업 표시줄 아이콘은 `assets/soundscrape.ico`를 함께 사용합니다.
기본 파형 디자인은 `assets/build-icon.ps1`에서 수정하고 실행하면 16~256px의
7가지 해상도를 담은 ICO를 다시 만들 수 있습니다. 다른 디자인으로 바꿀 때는
같은 경로의 ICO 파일을 교체한 뒤 EXE를 다시 빌드합니다.

## 실제 다운로드 검사

메타데이터 조회만 하는 검사가 아닙니다. 전체 오디오를 내려받은 다음 FFmpeg로
첫 15초가 디코딩되는지 검사하고 JSON 보고서를 남깁니다. 재검사할 때는 새로운
출력 폴더를 지정하세요.

```powershell
.\.venv\Scripts\python.exe -m soundscrape.smoke "https://soundcloud.com/ARTIST/TRACK" --output test-downloads/sc --report test-downloads/sc.json
.\.venv\Scripts\python.exe -m soundscrape.smoke "https://www.mixcloud.com/ARTIST/MIX/" --output test-downloads/mc --report test-downloads/mc.json
```

빌드된 EXE도 `--smoke-test URL --output FOLDER --report FILE`로 같은 검사를
지원합니다. EXE는 콘솔이 없으므로 프로세스 종료 코드와 JSON 보고서를 확인합니다.

## GitHub Actions / Release

**Actions → Windows desktop → Run workflow**에서 빌드하고 두 플랫폼의
**빌드된 EXE** 다운로드 검사를 실행합니다. 기본 공개 테스트 링크를 바꿀 수 있습니다. 테스트 파일 자체는
업로드하지 않고 JSON 보고서만 artifact로 남깁니다. 사이트의 일시적인 실패가
일반 PR 빌드를 막지 않도록 실시간 검사는 수동 실행 및 Release 태그 빌드에서 실행합니다.

`v*` 태그를 push하면 빌드와 두 플랫폼의 다운로드 검사가 성공한 뒤
Windows x64 EXE와 체크섬이 첨부된 **draft Release**를 만듭니다.
자동 빌드 결과와 다운로드 검사를 확인한 후 Release를 공개합니다.

```powershell
git tag v0.32.0
git push origin v0.32.0
```

---

## Legacy CLI documentation

![SoundScrape!](http://i.imgur.com/nHAt2ow.png)

SoundScrape [![Build Status](https://travis-ci.org/Miserlou/SoundScrape.svg)](https://travis-ci.org/Miserlou/SoundScrape) [![Python 3](https://img.shields.io/badge/Python-3-brightgreen.svg)](https://pypi.python.org/pypi/soundscrape/) [![PyPI](https://img.shields.io/pypi/v/soundscrape.svg)](https://pypi.python.org/pypi/SoundScrape)
==============

**SoundScrape** makes it super easy to download artists from SoundCloud (and Bandcamp and MixCloud) - even those which don't have download links! It automatically creates ID3 tags as well (including album art), which is handy.

Usage
---------

First, install it:

```bash
pip install soundscrape
```

Note that if you are having problems, please first try updating to the latest version:

```bash
pip install soundscrape --upgrade
```

Then, just call soundscrape and the name of the artist you want to scrape:

```bash
soundscrape rabbit-i-am
```

And you're done! Hooray! Files are stored as mp3s in the format **Artist name - Track title.mp3**.

You can also use the *-n* argument to only download a certain number of songs.

```bash
soundscrape rabbit-i-am -n 3
```

Sets
-------

Soundscrape can also download sets, but you have to include the full URL of the set you want to download:

```bash
soundscrape https://soundcloud.com/vsauce-awesome/sets/awesome
```

Groups
--------

Soundscrape can also download tracks from SoundCloud groups with the *-g* argument.

```bash
soundscrape chopped-and-screwed -gn 2
```

Tracks
--------

Soundscrape can also download specific tracks with *-t*:

```bash
soundscrape foolsgoldrecs -t danny-brown-dip
```

or with just the straight URL:

```bash
soundscrape https://soundcloud.com/foolsgoldrecs/danny-brown-dip
```

Likes
--------

Soundscrape can also download all of an Artist's Liked items with *-l*:

```bash
soundscrape troyboi -l
```

or with just the straight URL:

```bash
soundscrape https://soundcloud.com/troyboi/likes
```

High-Quality Downloads Only
--------

By default, SoundScrape will try to rip everything it can. However, if you only want to download tracks that have an official download available (which are typically at a higher-quality 320kbps bitrate), you can use the *-d* argument.

```bash
soundscrape sly-dogg -d
```

Keep Preview Tracks
--------

By default, SoundScrape will skip the 30-second preview tracks that SoundCloud now provides. You can choose to keep these preview snippets with the *-k* argument.

```bash
soundscrape chromeo -k
```

Folders
--------

By default, SoundScrape aims to act like _wget_, downloading in place in the current directory. With the *-f* argument, however, SoundScrape acts more like a download manager and sorts songs into the following format:

```
./ARTIST_NAME - ALBUM_NAME/SONG_NUMBER - SONG_TITLE.mp3
```

It will also skip previously downloaded tracks.

```bash
soundscrape murdercitydevils -f
```

Bandcamp
--------

SoundScrape can also pull down albums from Bandcamp. For Bandcamp pages, use the *-b* argument along with an artist's username or a specific URL. It only downloads one album at a time. This works with all of the other arguments, except *-d* as Bandcamp streams only come at one bitrate, as far as I can tell.

Note: Currently, when using the *-n* argument, the limit is evaluated for each album separately.

```bash
soundscrape warsaw -b -f
```

This also works for non-Bandcamp URLs that are hosted on Bandcamp:

```bash
soundscrape -b http://music.monstercat.com/
```

Note that the full URL must be included.

Mixcloud
--------

SoundScrape can also grab mixes from Mixcloud. This feature is extremely expermental and is in no way guaranteed to work!

Finds the original mp3 of a mix and grabs that (with tags and album art) if it can, or else just gets the raw m4a stream.

Mixcloud currently only takes an invidiual mix. Capacity for a whole artist's profile due shortly.

```bash
soundscrape https://www.mixcloud.com/corenewsuploads/flume-essential-mix-2015-10-03/ -of
```

Audiomack
--------

Just for fun, SoundScrape can also download individual songs from Audiomack. Not that you'd ever want to.

```bash
soundscrape -a http://www.audiomack.com/song/bottomfeedermusic/top-shottas
```

MusicBed
--------

For some strange reason, it also works for MusicBed.com. Thanks @brachna for this feature.

```bash
soundscrape https://www.musicbed.com/albums/be-still/2828
```

Opening Files
--------

As a convenience method, SoundScrape can automatically _'open'_ files that it downloads. This uses your system's 'open' command for file associations.

```bash
soundscrape lorn -of
```

Issues
-------

There's probably a lot more that can be done to improve this. Please file issues if you find them!
