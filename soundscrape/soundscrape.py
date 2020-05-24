#! /usr/bin/env python
"""Main SoundScrape module."""
from __future__ import unicode_literals

import argparse
import os
import re
import sys
import urllib
from datetime import datetime
from os import W_OK, access, mkdir
from os.path import dirname, exists, join
from subprocess import PIPE, Popen

import atoma
import demjson
import requests
import soundcloud
from clint.textui import colored, progress, puts
from mutagen import MutagenError
from mutagen.id3 import APIC
from mutagen.id3 import ID3 as OldID3
from mutagen.id3 import WXXX
from mutagen.mp3 import MP3, EasyMP3, HeaderNotFoundError
from sanitize_filename import sanitize

####################################################################

# Please be nice with this!
CLIENT_ID = "a3dd183a357fcff9a6943c0d65664087"
CLIENT_SECRET = "7e10d33e967ad42574124977cf7fa4b7"
MAGIC_CLIENT_ID = "b45b1aa10f1ac2941910a7f0d10f8e28"

AGGRESSIVE_CLIENT_ID = "OmTFHKYSMLFqnu2HHucmclAptedxWXkq"
APP_VERSION = "1481046241"

####################################################################


def main():
    """
    Argument parsing main function.

    Converts arguments to Python and processes accordingly.
    """
    # Hack related to #58
    if sys.platform == "win32":
        os.system("chcp 65001")

    parser = argparse.ArgumentParser(description="SoundScrape. Scrape an artist from SoundCloud.\n")
    parser.add_argument(
        "artist_url", metavar="U", type=str, nargs="*", help="An artist's SoundCloud username or URL",
    )
    parser.add_argument(
        "-n", "--num-tracks", type=int, default=sys.maxsize, help="The number of tracks to download",
    )
    parser.add_argument(
        "-g", "--group", action="store_true", help="Use if downloading tracks from a SoundCloud group",
    )
    parser.add_argument(
        "-b", "--bandcamp", action="store_true", help="Use if downloading from Bandcamp rather than SoundCloud",
    )
    parser.add_argument(
        "-a", "--audiomack", action="store_true", help="Use if downloading from Audiomack rather than SoundCloud",
    )
    parser.add_argument("-l", "--likes", action="store_true", help="Download all of a user's Likes.")
    parser.add_argument(
        "-L", "--login", type=str, default="soundscrape123@mailinator.com", help="Set login",
    )
    parser.add_argument(
        "-d", "--downloadable", action="store_true", help="Only fetch tracks with a downloadable link.",
    )
    parser.add_argument(
        "-t", "--track", type=str, default="", help="The name of a specific track by an artist",
    )
    parser.add_argument(
        "-f", "--folders", action="store_true", help="Organize saved songs in folders by artists",
    )
    parser.add_argument(
        "-p", "--path", type=str, default="", help="Set directory path where downloads should be saved to",
    )
    parser.add_argument("-P", "--password", type=str, default="soundscraperocks", help="Set password")
    parser.add_argument(
        "-o", "--open", action="store_true", help="Open downloaded files after downloading.",
    )
    parser.add_argument(
        "-v", "--version", action="store_true", default=False, help="Display the current version of SoundScrape",
    )

    args = parser.parse_args()
    vargs = vars(args)

    if vargs["version"]:
        import pkg_resources

        version = pkg_resources.require("soundscrape")[0].version
        print(version)
        return

    if not vargs["artist_url"]:
        parser.error("Please supply an artist's username or URL!")

    vargs["artist_url"] = urllib.parse.quote(vargs["artist_url"][0], safe=":/")

    if not exists(vargs["path"]):
        if not access(dirname(vargs["path"]), W_OK):
            vargs["path"] = ""
        else:
            mkdir(vargs["path"])

    if "bandcamp.com" in vargs["artist_url"] or vargs["bandcamp"]:
        process_bandcamp(vargs)
    elif "audiomack.com" in vargs["artist_url"] or vargs["audiomack"]:
        process_audiomack(vargs)
    elif "musicbed.com" in vargs["artist_url"]:
        process_musicbed(vargs)
    else:
        process_soundcloud(vargs)


####################################################################
# SoundCloud
####################################################################


def process_soundcloud(vargs):
    """
    Process SoundCloud download.

    Args:
        vargs (dict):

    """
    url = vargs["artist_url"].lower()
    track_permalink = vargs["track"].lower()
    num_tracks = vargs["num_tracks"]
    use_folders = vargs["folders"]
    custom_path = vargs["path"]
    downloadable_links_only = vargs["downloadable"]

    album = None
    artist = None
    filenames = []
    likes = False
    client = soundcloud.Client(client_id=CLIENT_ID)

    if "soundcloud" not in url.lower():
        if vargs["group"]:
            url = f"https://soundcloud.com/groups/{url}"
        elif len(track_permalink) > 0:
            url = f"https://soundcloud.com/{url}/{track_permalink}"
        else:
            url = f"https://soundcloud.com/{url}"
            if vargs["likes"] or "likes" in url.lower():
                likes = True

    if "likes" in url.lower():
        url = url[0 : url.find("/likes")]
        likes = True

    try:
        resolved = client.get("/resolve", url=url, limit=200)

        if likes:
            resolved = client.get(f"/users/{resolved.id}/favorites", limit=200, linked_partitioning=1)
            next_href = None
            if hasattr(resolved, "next_href"):
                next_href = resolved.next_href
            while next_href is not None:
                next_resolved = requests.get(next_href).json()
                next_href = None
                if "next_href" in next_resolved:
                    next_href = next_resolved["next_href"]
                next_resolved = soundcloud.resource.ResourceList(next_resolved["collection"])
                resolved.collection.extend(next_resolved)
            resolved = resolved.collection
    except Exception as e:
        filename = force_download_track_from_soundcloud(str(e), use_folders, custom_path)
        if filename is not None:
            filenames.append(filename)

    if not hasattr(resolved, "kind"):
        # This is either likes or sets.
        tracks = resolved
    elif resolved.kind == "playlist":
        album = resolved.title
        if len(resolved.tracks) > 0:
            tracks = resolved.tracks
        else:
            tracks = get_soundcloud_playlist_data(resolved.id)["tracks"]
    elif resolved.kind == "track":
        tracks = [resolved]
    elif resolved.kind == "group":
        tracks = client.get(f"/groups/{resolved.id}/tracks", limit=200)
    else:
        tracks = client.get(f"/users/{resolved.id}/tracks", limit=200)

    if hasattr(resolved, "full_name"):
        artist = resolved.full_name
        if artist == "":
            artist = resolved.username

    if len(tracks) == 0 and resolved.track_count > 0:
        # SoundCloud has a unfortunate bug where some artists don't have any tracks returned using:
        #   client.get("/users/" + artist_id + "/tracks", limit=200)
        # There are a number of reports of this issue since late 2019 on StackOverflow.
        # ( reference: https://stackoverflow.com/questions/59204383, https://stackoverflow.com/questions/61807979)
        # It seems that the common pattern is that if an artist has any tracks marked as private,
        # e.g. the track is not downloadable (only streamable), then SoundCloud won't return any
        # tracks for that artist. The way around this is to refer to the artist's RSS feed. This
        # is in the form of:
        #   http://feeds.soundcloud.com/users/soundcloud:users:<artist_id>/sounds.rss

        filenames = download_tracks_from_soundcloud_feed(resolved.id, artist, num_tracks, use_folders, custom_path)
    else:
        filenames = download_tracks_from_soundcloud(
            client, tracks, artist, album, num_tracks, downloadable_links_only, use_folders, custom_path,
        )

    if vargs["open"]:
        open_files(filenames)

    return


def force_download_track_from_soundcloud(message, use_folders=False, custom_path=""):
    """
    Try to force download a track from SoundCloud despite a client error.

    Args:
        message (str):
        use_folder (bool):
        custom_path (str):

    Returns:
        filename of successfully downloaded track or None

    """
    if "404" in message.lower():
        puts(colored.red("Problem downloading [404]: ") + colored.white("Item Not Found"))
        return None

    item_id = message.rsplit("/", 1)[-1].split(".json")[0].split("?client_id")[0]
    url = get_soundcloud_track_url(item_id)
    response = requests.get(url)
    if response.status_code != 200:
        puts(colored.red("Problem downloading: ") + colored.white(url))
        return None

    title_tag = response.text.split("<title>")[1].split("</title")[0]

    track_data = {
        "url": url,
        "artist": title_tag.split(" by ")[1].split("|")[0].strip(),
        "title": title_tag.split(" by ")[0].strip(),
    }
    return download_single_track_from_soundcloud(track_data, use_folders, custom_path)


def download_tracks_from_soundcloud_feed(track_id, artist, num_tracks=sys.maxsize, use_folders=False, custom_path=""):
    """
    Use the artist's RSS feed from SoundCloud to get tracks.

    Args:
        track_id (int):
        artist (str):
        num_tracks (int):
        use_folders (bool):
        custom_path (str):

    Returns:
        filenames downloaded from the RSS feed

    """
    filenames = []
    url = f"http://feeds.soundcloud.com/users/soundcloud:users:{track_id}/sounds.rss"
    response = requests.get(url)
    if response.status_code != 200:
        puts(colored.red("Problem downloading: ") + colored.white(url))
        return None

    feed = atoma.parse_rss_bytes(response.content)
    for i, feed_item in enumerate(feed.items):
        if i > num_tracks - 1:
            continue

        for enclosure in feed_item.enclosures:
            track_data = {
                "url": enclosure.url,
                "artist": artist,
                "title": feed_item.title,
                "date": feed_item.pub_date.year,
                "artwork_url": feed.image.url,
            }

            filename = download_single_track_from_soundcloud(track_data, use_folders, custom_path)
            if filename is not None:
                filenames.append(filename)
    return filenames


def download_single_track_from_soundcloud(track_data, use_folders=False, custom_path=""):
    """
    Download a single track from SoundCloud.

    Args:
        track_data (dict):
        use_folders (bool):
        custom_path (str):

    Returns:
        filename or None

    """
    required_keys = {"artist", "title", "url"}
    if not track_data.keys() >= required_keys:
        return None

    filename = sanitize(f"{track_data['artist']} - {track_data['title']}.mp3")

    if use_folders:
        name_path = join(custom_path, track_data["artist"])
        if not exists(name_path):
            mkdir(name_path)
        filename = join(name_path, filename)
    else:
        filename = join(custom_path, filename)

    if exists(filename):
        puts_safe(colored.yellow("Track already downloaded: ") + colored.white(track_data["title"]))
        return None

    puts_safe(colored.green("Scraping: ") + colored.white(track_data["title"]))

    filename = download_file(track_data["url"], filename)

    tagged = tag_file(
        filename,
        artist=track_data["artist"],
        title=track_data["title"],
        album=track_data.get("album"),
        year=track_data.get("date"),
        genre=track_data.get("genre"),
        artwork_url=track_data.get("artwork_url"),
    )
    if not tagged:
        wav_filename = f"{filename[:-3]}wav"
        os.rename(filename, wav_filename)
        filename = wav_filename

    return filename


def download_tracks_from_soundcloud(
    client, tracks, artist, album, num_tracks=sys.maxsize, downloadable_links_only=False, use_folders=False, custom_path="",
):
    """Given a list of tracks, iteratively download all of them."""
    filenames = []

    for i, track in enumerate(tracks):
        track_id = track.id if hasattr(track, "id") else track.get("id", "")
        title = track.title if hasattr(track, "title") else track.get("title", "")

        if hasattr(track, "kind") and track.kind == "playlist":
            if len(track.tracks) > 0:
                playlist_tracks = track.tracks
            else:
                playlist_tracks = get_soundcloud_playlist_data(track_id)
                playlist_tracks = playlist_tracks["tracks"] if playlist_tracks is not None else None
            if playlist_tracks is not None:
                download_tracks_from_soundcloud(
                    client, playlist_tracks, artist, album, num_tracks, downloadable_links_only, use_folders, custom_path,
                )
            else:
                puts_safe(colored.white(title) + colored.red(" is not downloadable."))
            continue

        track_data = {}

        user = track.user if hasattr(track, "user") else track.get("user")
        track_artist = artist
        if user is not None:
            track_artist = user["full_name"] if user.get("full_name") is not None else user["username"]

        track_data = {
            "direct": False,
            "artist": artist if artist is not None else track_artist,
            "album": album,
            "title": title,
            "streamable": track.streamable if hasattr(track, "streamable") else track.get("streamable", False),
            "date": track.release if hasattr(track, "release") else track.get("release"),
            "genre": track.genre if hasattr(track, "genre") else track.get("genre"),
            "artwork_url": track.artwork_url if hasattr(track, "artwork_url") else track.get("artwork_url"),
        }
        if track.downloadable if hasattr(track, "downloadable") else track.get("downloadable", False):
            track_data["url"] = track.download_url if hasattr(track, "download_url") else track.get("download_url")
        else:
            if downloadable_links_only:
                puts_safe(colored.red("Skipping: ") + colored.white(title))
                continue
            if hasattr(track, "stream_url") or isinstance(track, dict):
                track_data["url"] = track.stream_url if hasattr(track, "stream_url") else track.get("stream_url")
            else:
                track_data["url"] = get_soundcloud_track_url(track_id)
                track_data["direct"] = True

        if track_data["url"] is None:
            puts_safe(colored.white(title) + colored.red(" is not downloadable."))
            continue

        if i > num_tracks - 1:
            continue
        try:
            if not track_data["direct"]:
                stream = client.get(track_data["url"], allow_redirects=False, limit=200)
                if hasattr(stream, "location"):
                    track_data["url"] = stream.location
                else:
                    track_data["url"] = stream.url

            filename = download_single_track_from_soundcloud(track_data, use_folders, custom_path)
            if filename is not None:
                filenames.append(filename)
        except Exception as e:
            filename = force_download_track_from_soundcloud(str(e), use_folders, custom_path)
            if filename is not None:
                filenames.append(filename)
            else:
                puts_safe(colored.red("Problem downloading ") + colored.white(track_data["title"]))

    return filenames


def get_soundcloud_playlist_data(playlist_id):
    """
    Get playlist data from SoundCloud.

    Args:
        playlist_id (str): id of the playlist

    Returns:
        data about the playlist with playlist_id or None

    """
    url = f"https://api.soundcloud.com/playlists/{playlist_id}?representation=full&client_id=02gUJC0hH2ct1EGOcYXQIzRFU91c72Ea&app_version=1467724310"
    response = requests.get(url)
    if response.status_code != 200:
        puts(colored.red("Problem getting playlist data from: ") + colored.white(url))
        return None

    return response.json()


def get_soundcloud_track_url(track_id):
    """
    Get the track url from SoundCloud.

    Args:
        track_id (str): id of the track

    Returns:
        url to the track with track_id or None

    """
    url = (
        f"https://api.soundcloud.com/i1/tracks/{track_id}/streams/?client_id={AGGRESSIVE_CLIENT_ID}&app_version={APP_VERSION}"
    )
    response = requests.get(url)
    if response.status_code != 200:
        puts(colored.red("Problem getting track data from: ") + colored.white(url))
        return None

    json_response = response.json()
    return json_response["http_mp3_128_url"]


####################################################################
# Bandcamp
####################################################################


def process_bandcamp(vargs):
    """
    Process BandCamp download.

    Args:
        vargs (dict):
    """
    artist_url = vargs["artist_url"]

    if "bandcamp.com" in artist_url or ("://" in artist_url and vargs["bandcamp"]):
        bc_url = artist_url
    else:
        bc_url = f"https://{artist_url}.bandcamp.com/music"

    filenames = scrape_bandcamp_url(
        bc_url, num_tracks=vargs["num_tracks"], use_folders=vargs["folders"], custom_path=vargs["path"],
    )

    # check if we have lists inside a list, which indicates the
    # scraping has gone recursive, so we must format the output
    # ( reference: http://stackoverflow.com/a/5251706 )
    if any(isinstance(elem, list) for elem in filenames):
        # first, remove any empty sublists inside our outter list
        # ( reference: http://stackoverflow.com/a/19875634 )
        filenames = [sub for sub in filenames if sub]
        # now, make sure we "flatten" the list
        # ( reference: http://stackoverflow.com/a/11264751 )
        filenames = [val for sub in filenames for val in sub]

    if vargs["open"]:
        open_files(filenames)

    return


# Largely borrowed from bandcampscrape
# ( reference: https://github.com/ronier/bandcampscrape)
def scrape_bandcamp_url(url, num_tracks=sys.maxsize, use_folders=False, custom_path=""):
    """
    Pull out artist and track info from a Bandcamp URL.

    Returns:
        list: filenames to open

    """
    filenames = []
    album_data = get_bandcamp_metadata(url)

    # If it's a list, we're dealing with a list of Album URLs,
    # so we call the scrape_bandcamp_url() method for each one
    if type(album_data) is list:
        for album_url in album_data:
            filenames.append(scrape_bandcamp_url(album_url, num_tracks, use_folders, custom_path))
        return filenames

    artist = album_data["artist"]
    album_name = album_data["album_name"]

    if use_folders:
        if album_name:
            directory = f"{artist} - {album_name}"
        else:
            directory = artist
        directory = sanitize(directory)
        directory = join(custom_path, directory)
        if not exists(directory):
            mkdir(directory)

    for i, track in enumerate(album_data["trackinfo"]):
        if i > num_tracks - 1:
            continue
        try:
            track_name = track["title"]
            if track["track_num"]:
                track_number = str(track["track_num"]).zfill(2)
            else:
                track_number = None
            if track_number and use_folders:
                track_filename = f"{track_number} - {track_name}.mp3"
            else:
                track_filename = f"{track_name}.mp3"
            track_filename = sanitize(track_filename)

            if use_folders:
                path = join(directory, track_filename)
            else:
                path = join(custom_path, sanitize(artist) + " - " + track_filename)

            if exists(path):
                puts_safe(colored.yellow("Track already downloaded: ") + colored.white(track_name))
                continue

            if not track["file"]:
                puts_safe(colored.yellow("Track unavailable for scraping: ") + colored.white(track_name))
                continue

            puts_safe(colored.green("Downloading") + colored.white(": " + track_name))
            path = download_file(track["file"]["mp3-128"], path)

            album_year = album_data["album_release_date"]
            if album_year:
                album_year = datetime.strptime(album_year, "%d %b %Y %H:%M:%S GMT").year

            tag_file(
                path,
                artist,
                track_name,
                album=album_name,
                year=album_year,
                genre=album_data["genre"],
                artwork_url=album_data["artFullsizeUrl"],
                track_number=track_number,
                url=album_data["url"],
            )

            filenames.append(path)

        except:
            puts_safe(colored.red("Problem downloading ") + colored.white(track_name))

    return filenames


def get_bandcamp_metadata(url):
    """
    Read information from the Bandcamp JavaScript object.

    The method may return a list of URLs (indicating this is probably a "main" page which links to one or more albums),
    or a JSON if we can already parse album/track info from the given url.
    The JSON is "sloppy". The native python JSON parser often can't deal, so we use the more tolerant demjson instead.
    """
    response = requests.get(url)
    try:
        sloppy_json = response.text.split("var TralbumData = ")
        sloppy_json = sloppy_json[1].replace('" + "', "")
        sloppy_json = sloppy_json.replace("'", "'")
        sloppy_json = sloppy_json.split("};")[0] + "};"
        sloppy_json = sloppy_json.replace("};", "}")
        output = demjson.decode(sloppy_json)
    # if the JSON parser failed, we should consider it's a "/music" page,
    # so we generate a list of albums/tracks and return it immediately
    except:
        regex_all_albums = r'<a href="(/(?:album|track)/[^>]+)">'
        all_albums = re.findall(regex_all_albums, response.text, re.MULTILINE)
        album_url_list = list()
        for album in all_albums:
            album_url = re.sub(r"music/?$", "", url) + album
            album_url_list.append(album_url)
        return album_url_list
    # if the JSON parser was successful, use a regex to get all tags
    # from this album/track, join them and set it as the "genre"
    regex_tags = r'<a class="tag" href[^>]+>([^<]+)</a>'
    tags = re.findall(regex_tags, response.text, re.MULTILINE)
    # make sure we treat integers correctly with join()
    # according to http://stackoverflow.com/a/7323861
    # (very unlikely, but better safe than sorry!)
    output["genre"] = " ".join(s for s in tags)
    # make sure we always get the correct album name, even if this is a
    # track URL (unless this track does not belong to any album, in which
    # case the album name remains set as None.
    output["album_name"] = None
    regex_album_name = r'album_title\s*:\s*"([^"]+)"\s*,'
    match = re.search(regex_album_name, response.text, re.MULTILINE)
    if match:
        output["album_name"] = match.group(1)

    try:
        artUrl = response.text.split('"tralbumArt">')[1].split('">')[0].split('href="')[1]
        output["artFullsizeUrl"] = artUrl
    except:
        puts_safe(colored.red("Couldn't get full artwork."))
        output["artFullsizeUrl"] = None

    return output


####################################################################
# Audiomack
####################################################################


def process_audiomack(vargs):
    """
    Process Audiomack download.

    Args:
        vargs (dict):
    """
    artist_url = vargs["artist_url"]

    if "audiomack.com" in artist_url:
        mc_url = artist_url
    else:
        mc_url = f"https://audiomack.com/{artist_url}"

    filenames = scrape_audiomack_url(
        mc_url, num_tracks=vargs["num_tracks"], use_folders=vargs["folders"], custom_path=vargs["path"],
    )

    if vargs["open"]:
        open_files(filenames)

    return


def scrape_audiomack_url(mc_url, num_tracks=sys.maxsize, use_folders=False, custom_path=""):
    """
    Pull out artist and track info from a Audiomack URL.

    Returns:
        list: filenames to open

    """
    filenames = []

    try:
        data = get_audiomack_data(mc_url)
    except:
        puts_safe(colored.red("Problem downloading ") + mc_url)
        return filenames

    track_artist = sanitize(data["artist"])
    track_title = sanitize(data["title"])
    track_filename = f"{track_artist} - {track_title}.mp3"

    if use_folders:
        track_artist_path = join(custom_path, track_artist)
        if not exists(track_artist_path):
            mkdir(track_artist_path)
        track_filename = join(track_artist_path, track_filename)
    else:
        track_filename = join(custom_path, track_filename)

    if exists(track_filename):
        puts_safe(colored.yellow("Skipping: ") + colored.white(data["title"]) + colored.yellow(" - already exists!"))
        return filenames

    puts_safe(colored.green("Downloading: ") + colored.white(f"{data['artist']} - {data['title']}"))
    download_file(data["mp3_url"], track_filename)
    tag_file(
        track_filename,
        artist=data["artist"],
        title=data["title"],
        year=data["year"],
        artwork_url=data["artwork_url"],
    )
    filenames.append(track_filename)

    return filenames


def get_audiomack_data(url):
    """
    Scrapes a Auidomack page for a track's important information.

    Returns:
        dict: containing audio data

    """
    response = requests.get(url)

    mp3_url = response.text.split('class="player-icon download-song" title="Download" href="')[1].split('"')[0]
    artist = response.text.split('<span class="artist">')[1].split("</span>")[0].strip()
    title = response.text.split('<span class="artist">')[1].split("</span>")[1].split("</h1>")[0].strip()
    artwork_url = response.text.split('<a class="lightbox-trigger" href="')[1].split('" data')[0].strip()

    data = {
    "mp3_url": mp3_url,
    "title": title,
    "artist": artist,
    "artwork_url": artwork_url,
    }

    return data


####################################################################
# MusicBed
####################################################################


def process_musicbed(vargs):
    """
    Process MusicBed download.

    Args:
        vargs (dict):
    """
    validated = False
    if vargs["artist_url"].startswith("https://www.musicbed.com/"):
        splitted = vargs["artist_url"][len("https://www.musicbed.com/") :].split("/")
        if len(splitted) == 3:
            if (splitted[0] == "artists" or splitted[0] == "albums" or splitted[0] == "songs") and splitted[2].isdigit():
                validated = True

    if not validated:
        puts(colored.red("process_musicbed: you provided incorrect MusicBed url. Aborting."))
        puts(colored.white("Please make sure that url is either artist-url, album-url or song-url."))
        puts(colored.white("Example of correct artist-url: https://www.musicbed.com/artists/lights-motion/5188"))
        puts(colored.white("Example of correct album-url:  https://www.musicbed.com/albums/be-still/2828"))
        puts(colored.white("Example of correct song-url:   https://www.musicbed.com/songs/be-still/24540"))
        return

    filenames = scrape_musicbed_url(
        vargs["artist_url"],
        vargs["login"],
        vargs["password"],
        num_tracks=vargs["num_tracks"],
        use_folders=vargs["folders"],
        custom_path=vargs["path"],
    )

    if vargs["open"]:
        open_files(filenames)

    return


def scrape_musicbed_url(url, login, password, num_tracks=sys.maxsize, use_folders=False, custom_path=""):
    """
    Scrapes provided MusicBed URL.

    Uses requests' Session object in order to store cookies.
    Requires login and password information.
    If provided url is of pattern 'https://www.musicbed.com/artists/<string>/<number>' - a number of albums will be downloaded.
    If provided url is of pattern 'https://www.musicbed.com/albums/<string>/<number>'  - only one album will be downloaded.
    If provided url is of pattern 'https://www.musicbed.com/songs/<string>/<number>'   - will be treated as one album (but download only 1st track).
    Metadata and urls are obtained from JavaScript data that's treated as JSON data.

    Returns:
        list: filenames to open

    """
    session = requests.Session()

    response = session.get(url)
    if response.status_code != 200:
        puts(colored.red(f"scrape_musicbed_url: couldn't open provided url. Status code: {response.status_code}. Aborting."))
        session.close()
        return []

    albums = []
    # let's determine what url type we got
    # '/artists/' - search for and download many albums
    # '/albums/'  - means we're downloading 1 album
    # '/songs/'   - means 1 album as well, but we're forcing num_tracks=1 in order to download only first relevant track
    if url.startswith("https://www.musicbed.com/artists/"):
        # a hackjob code to get a list of available albums
        main_index = 0
        while response.text.find("https://www.musicbed.com/albums/", main_index) != -1:
            start_index = response.text.find("https://www.musicbed.com/albums/", main_index)
            end_index = response.text.find('">', start_index)
            albums.append(response.text[start_index:end_index])
            main_index = end_index
    elif url.startswith("https://www.musicbed.com/songs/"):
        albums.append(url)
        num_tracks = 1
    else:  # url.startswith( 'https://www.musicbed.com/albums/' )
        albums.append(url)

    # let's get our token and try to login (csrf_token seems to be present on every page)
    token = response.text.split('var csrf_token = "')[1].split('";')[0]
    details = {"_token": token, "login": login, "password": password}
    response = session.post("https://www.musicbed.com/ajax/login", data=details)
    if response.status_code != 200:
        puts(colored.red("scrape_musicbed_url: couldn't login. Aborting. ") + colored.white("Couldn't access login page."))
        session.close()
        return []
    login_response_data = demjson.decode(response.text)
    if not login_response_data["body"]["status"]:
        puts(colored.red("Can't login to MusicBed. ") + colored.white("Did you provide correct login and password?"))
        session.close()
        return []

    # now let's actually scrape collected pages
    filenames = []
    for each_album_url in albums:
        response = session.get(each_album_url)
        if response.status_code != 200:
            puts_safe(
                colored.red(
                    f"scrape_musicbed_url: couldn't open url: {each_album_url}. Status code: {response.status_code}. Skipping."
                )
            )
            continue

        # actually not a JSON, but a JS object, but so far so good
        json = response.text.split("App.components.SongRows = ")[1].split("</script>")[0]
        data = demjson.decode(json)

        song_count = 1
        for each_song in data["loadedSongs"]:
            if song_count > num_tracks:
                break

            try:
                url, params = each_song["playback_url"].split("?")

                details = dict()
                for each_param in params.split("&"):
                    name, value = each_param.split("=")
                    details.update({name: value})
                # musicbed warns about it if it's not fixed
                details["X-Amz-Credential"] = details["X-Amz-Credential"].replace("%2F", "/")

                directory = custom_path
                if use_folders:
                    sanitized_artist = sanitize(each_song["album"]["data"]["artist"]["data"]["name"])
                    sanitized_album = sanitize(each_song["album"]["data"]["name"])
                    directory = join(directory, sanitized_artist + " - " + sanitized_album)
                    if not exists(directory):
                        mkdir(directory)
                filename = join(directory, str(song_count) + " - " + sanitize(each_song["name"]) + ".mp3",)

                if exists(filename):
                    puts_safe(
                        colored.yellow("Skipping: ") + colored.white(each_song["name"]) + colored.yellow(" - already exists!")
                    )
                    song_count += 1
                    continue

                puts_safe(colored.green("Downloading: ") + colored.white(each_song["name"]))
                path = download_file(url, filename, session=session, params=details)

                # example of genre_string:
                # "<a href=\"https://www.musicbed.com/genres/ambient/2\">Ambient</a> <a href=\"https://www.musicbed.com/genres/cinematic/4\">Cinematic</a>"
                genres = ""
                for each in each_song["genre_string"].split("</a>"):
                    if each != "":
                        genres += each.split('">')[1] + "/"
                genres = genres[:-1]  # removing last '/

                tag_file(
                    path,
                    each_song["album"]["data"]["artist"]["data"]["name"],
                    each_song["name"],
                    album=each_song["album"]["data"]["name"],
                    year=int(each_song["album"]["data"]["released_at"].split("-")[0]),
                    genre=genres,
                    artwork_url=each_song["album"]["data"]["imageObject"]["data"]["paths"]["original"],
                    track_number=str(song_count),
                    url=each_song["song_url"],
                )

                filenames.append(path)
                song_count += 1
            except:
                puts_safe(colored.red("Problem downloading ") + colored.white(f"{each_song['name']}. Skipping."))
                song_count += 1

    session.close()

    return filenames


####################################################################
# File Utility
####################################################################


def download_file(url, path, session=None, params=None):
    """Download an individual file."""
    if url[0:2] == "//":
        url = f"https://{url[2:]}"

    # Use a temporary file so that we don't import incomplete files.
    tmp_path = f"{path}.tmp"

    if session is not None and params is not None:
        r = session.get(url, params=params, stream=True)
    elif session is not None and params is None:
        r = session.get(url, stream=True)
    else:
        r = requests.get(url, stream=True)
    with open(tmp_path, "wb") as f:
        total_length = int(r.headers.get("content-length", 0))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length / 1024) + 1):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()

    os.rename(tmp_path, path)

    return path


def tag_file(
    filename, artist, title, year=None, genre=None, artwork_url=None, album=None, track_number=None, url=None,
):
    """
    Attempt to put ID3 tags on a file.

    Args:
        artist (str):
        title (str):
        year (int):
        genre (str):
        artwork_url (str):
        album (str):
        track_number (str):
        filename (str):
        url (str):

    """
    saved_correctly = True

    try:
        audio = EasyMP3(filename)
    except HeaderNotFoundError:
        puts(colored.red("Problem opening file: ") + colored.white("Is this file a WAV?"))
        return False

    audio.tags = None
    audio["artist"] = artist
    audio["title"] = title
    if year is not None:
        # TODO: move year to date.
        audio["date"] = str(year)
    if album is not None:
        audio["album"] = album
    if track_number is not None:
        audio["tracknumber"] = track_number
    if genre is not None:
        audio["genre"] = genre
    if url is not None:
        # saves the tag as WOAR
        audio["website"] = url

    try:
        audio.save()
    except MutagenError:
        puts(colored.red("Problem tagging file: ") + colored.white("Is this file a WAV?"))
        saved_correctly = False

    try:
        audio = MP3(filename, ID3=OldID3)
    except HeaderNotFoundError:
        puts(colored.red("Problem opening file: ") + colored.white("Is this file a WAV?"))
        return False

    if artwork_url is not None:
        mime = "image/jpeg"
        artwork_url = artwork_url.replace("https", "http")
        urls = [artwork_url]
        if "-large" in artwork_url:
            urls.insert(0, artwork_url.replace("-large", "-t500x500"))

        for a_url in urls:
            response = requests.get(a_url)
            if response.status_code != 200:
                continue

            if ".png" in a_url:
                mime = "image/png"

            # encoding=3 means utf-8
            # type=3 means cover image
            audio.tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=response.content))
            break

    if url is not None:
        # Some software doesn't seem to use WOAR so the url is saved again as WXXX.
        audio.tags.add(WXXX(encoding=3, url=url))

    try:
        audio.save()
    except MutagenError:
        puts(colored.red("Problem tagging file: ") + colored.white("Is this file a WAV?"))
        saved_correctly = False

    return saved_correctly


def open_files(filenames):
    """
    Call the system 'open' command on a file.

    Args:
        filenames (list):
    """
    if len(filenames) == 0:
        return

    command = ["open"] + filenames
    process = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()


def puts_safe(text):
    """
    Safely write to the screen.

    Args:
        text (str):
    """
    if sys.platform == "win32":
        puts(text.encode(sys.stdout.encoding, errors="replace").decode())
    else:
        puts(text)


####################################################################
# Main
####################################################################

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(e)
