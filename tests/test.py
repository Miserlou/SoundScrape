"""Tests for SoundScrape."""
import glob
import os

from soundscrape.soundscrape import process_bandcamp, process_soundcloud


def cleanup_files():
    """Cleanup files from tests."""
    for f in glob.glob("*.mp3"):
        os.unlink(f)
    for f in glob.glob("*.m4a"):
        os.unlink(f)


def test_soundcloud_full_url():
    """Basic SoundCloud test with full url."""
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


def test_soundcloud_full_url_2():
    """Basic SoundCloud test with full url."""
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


def test_soundcloud_artist_only():
    """Basic SoundCloud test with artist name only."""
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
        "artist_url": "hd1080pmusic",
        "keep": False,
    }
    process_soundcloud(vargs)
    new_mp3_count = len(glob.glob1("", "*.mp3"))
    assert new_mp3_count > mp3_count
    assert new_mp3_count == 1
    cleanup_files()


def test_soundcloud_tracks():
    """Basic SoundCloud test tracks."""
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
        "artist_url": "https://soundcloud.com/alan-seslowsky/tracks",
        "keep": False,
    }
    process_soundcloud(vargs)
    new_mp3_count = len(glob.glob1("", "*.mp3"))
    assert new_mp3_count > mp3_count
    assert new_mp3_count == 1
    cleanup_files()


def test_soundcloud_track_not_found():
    """Basic SoundCloud test with a track that can't be found."""
    cleanup_files()
    vargs = {
        "path": "",
        "folders": False,
        "group": False,
        "track": "danny-brown-dip",
        "num_tracks": 1,
        "bandcamp": False,
        "downloadable": False,
        "likes": False,
        "open": False,
        "artist_url": "foolsgoldrecs",
        "keep": False,
    }
    process_soundcloud(vargs)
    new_mp3_count = len(glob.glob1("", "*.mp3"))
    assert new_mp3_count == 0
    cleanup_files()


def test_soundcloud_feed_download():
    """Basic SoundCloud feed test."""
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
        "artist_url": "https://soundcloud.com/johnocallaghan",
        "keep": False,
    }
    process_soundcloud(vargs)
    new_mp3_count = len(glob.glob1("", "*.mp3"))
    assert new_mp3_count > mp3_count
    assert new_mp3_count == 1
    cleanup_files()


def test_bandcamp():
    """Basic BandCamp test."""
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
    """Basic BandCamp test."""
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
