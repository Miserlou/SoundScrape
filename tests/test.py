import glob
import os

from soundscrape.soundscrape import process_soundcloud
from soundscrape.soundscrape import process_bandcamp


def cleanup_files():
    for f in glob.glob("*.mp3"):
        os.unlink(f)
    for f in glob.glob("*.m4a"):
        os.unlink(f)


def test_soundcloud():
    cleanup_files()

    mp3_count = len(glob.glob1("", "*.mp3"))
    vargs = {
        "path": "",
        "folders": False,
        "group": False,
        "track": "",
        "num_tracks": 9223372036854775807,
        "bandcamp": False,
        "downloadable": False,
        "likes": False,
        "open": False,
        "artist_url": "https://soundcloud.com/fzpz/revised",
        "keep": True,
    }
    process_soundcloud(vargs)
    new_mp3_count = len(glob.glob1("", "*.mp3"))
    assert new_mp3_count > mp3_count
    cleanup_files()


def test_soundcloud_hard():
    cleanup_files()
    mp3_count = len(glob.glob1("", "*.mp3"))
    vargs = {
        "path": "",
        "folders": False,
        "group": False,
        "track": "",
        "num_tracks": 1,
        "bandcamp": False,
        "downloadable": False,
        "likes": False,
        "open": False,
        "artist_url": "https://soundcloud.com/lostdogz/snuggles-chapstick",
        "keep": False,
    }
    process_soundcloud(vargs)
    new_mp3_count = len(glob.glob1("", "*.mp3"))
    assert new_mp3_count > mp3_count
    assert new_mp3_count == 1
    cleanup_files()


def test_bandcamp():
    cleanup_files()
    mp3_count = len(glob.glob1("", "*.mp3"))
    vargs = {
        "path": "",
        "folders": False,
        "group": False,
        "track": "",
        "num_tracks": 9223372036854775807,
        "bandcamp": False,
        "downloadable": False,
        "likes": False,
        "open": False,
        "artist_url": "https://atenrays.bandcamp.com/track/who-u-think",
    }
    process_bandcamp(vargs)
    new_mp3_count = len(glob.glob1("", "*.mp3"))
    assert new_mp3_count > mp3_count
    cleanup_files()


def test_bandcamp_slashes():
    cleanup_files()
    mp3_count = len(glob.glob1("", "*.mp3"))
    vargs = {
        "path": "",
        "folders": False,
        "group": False,
        "track": "",
        "num_tracks": 9223372036854775807,
        "bandcamp": False,
        "downloadable": False,
        "likes": False,
        "open": False,
        "artist_url": "https://defill.bandcamp.com/track/amnesia-chamber-harvest-skit",
    }
    process_bandcamp(vargs)
    new_mp3_count = len(glob.glob1("", "*.mp3"))
    assert new_mp3_count > mp3_count
    cleanup_files()


def test_mixcloud():
    cleanup_files()
    # shortest mix I could find that was still semi tolerable
    # mp3_count = len(glob.glob1('', "*.mp3"))
    # m4a_count = len(glob.glob1('', "*.m4a"))
    # vargs = {'path':'', 'folders': False, 'group': False, 'track': '', 'num_tracks': 9223372036854775807, 'bandcamp': False, 'downloadable': False, 'likes': False, 'open': False, 'artist_url': 'https://www.mixcloud.com/Bobby_T_FS15/coffee-cigarettes-saturday-morning-hip-hop-fix/'}
    # process_mixcloud(vargs)
    # new_mp3_count = len(glob.glob1('', "*.mp3"))
    # new_m4a_count = len(glob.glob1('', "*.m4a"))
    # self.assertTrue((new_mp3_count > mp3_count) or (new_m4a_count > m4a_count))
    cleanup_files()
