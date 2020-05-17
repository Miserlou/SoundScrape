#! /usr/bin/env python
from __future__ import unicode_literals

import argparse
import atoma
import demjson
import os
import re
import requests
import soundcloud
import sys
import urllib

from clint.textui import colored, puts, progress
from datetime import datetime
from mutagen.mp3 import MP3, EasyMP3
from mutagen.id3 import APIC, WXXX
from mutagen.id3 import ID3 as OldID3
from subprocess import Popen, PIPE
from os.path import dirname, exists, join
from os import access, mkdir, W_OK

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
    Main function.

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
        "-m", "--mixcloud", action="store_true", help="Use if downloading from Mixcloud rather than SoundCloud",
    )
    parser.add_argument(
        "-a", "--audiomack", action="store_true", help="Use if downloading from Audiomack rather than SoundCloud",
    )
    parser.add_argument("-l", "--likes", action="store_true", help="Download all of a user's Likes.")
    parser.add_argument(
        "-L", "--login", type=str, default="soundscrape123@mailinator.com", help="Set login",
    )
    parser.add_argument(
        "-d", "--downloadable", action="store_true", help="Only fetch tracks with a Downloadable link.",
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
    parser.add_argument("-k", "--keep", action="store_true", help="Keep 30-second preview tracks")
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

    artist_url = vargs["artist_url"]

    if not exists(vargs["path"]):
        if not access(dirname(vargs["path"]), W_OK):
            vargs["path"] = ""
        else:
            mkdir(vargs["path"])

    if "bandcamp.com" in artist_url or vargs["bandcamp"]:
        process_bandcamp(vargs)
    elif "mixcloud.com" in artist_url or vargs["mixcloud"]:
        process_mixcloud(vargs)
    elif "audiomack.com" in artist_url or vargs["audiomack"]:
        process_audiomack(vargs)
    elif "musicbed.com" in artist_url:
        process_musicbed(vargs)
    else:
        process_soundcloud(vargs)


####################################################################
# SoundCloud
####################################################################


def process_soundcloud(vargs):
    """Main SoundCloud path."""
    artist_url = vargs["artist_url"].lower()
    track_permalink = vargs["track"].lower()
    keep_previews = vargs["keep"]
    folders = vargs["folders"]

    id3_extras = {}
    one_track = False
    num_tracks = 1
    likes = False
    client = soundcloud.Client(client_id=CLIENT_ID)

    if "soundcloud" not in artist_url.lower():
        if vargs["group"]:
            artist_url = f"https://soundcloud.com/groups/{artist_url}"
        elif len(track_permalink) > 0:
            one_track = True
            track_url = f"https://soundcloud.com/{artist_url}/{track_permalink}"
        else:
            artist_url = f"https://soundcloud.com/{artist_url}"
            if vargs["likes"] or "likes" in artist_url.lower():
                likes = True

    if "likes" in artist_url.lower():
        artist_url = artist_url[0 : artist_url.find("/likes")]
        likes = True

    if not one_track:
        num_tracks = vargs["num_tracks"]

    try:
        if one_track:
            resolved = client.get("/resolve", url=track_url, limit=200)
        elif likes:
            userId = str(client.get("/resolve", url=artist_url).id)
            resolved = client.get(f"/users/{userId}/favorites", limit=200, linked_partitioning=1)
            next_href = False
            if hasattr(resolved, "next_href"):
                next_href = resolved.next_href
            while next_href:
                resolved2 = requests.get(next_href).json()
                if "next_href" in resolved2:
                    next_href = resolved2["next_href"]
                else:
                    next_href = False
                resolved2 = soundcloud.resource.ResourceList(resolved2["collection"])
                resolved.collection.extend(resolved2)
            resolved = resolved.collection
        else:
            resolved = client.get("/resolve", url=artist_url, limit=200)
    except Exception as e:
        # SoundCloud is trying to prevent us from downloading this.
        # Instead of utilizing the API/client we will do all our own scraping. Boo.

        if "404 Client Error" in str(e):
            puts(colored.red("Problem downloading [404]: ") + colored.white("Item Not Found"))
            return None

        message = str(e)
        item_id = message.rsplit("/", 1)[-1].split(".json")[0].split("?client_id")[0]
        hard_track_url = get_hard_track_url(item_id)

        track_data = {}
        request = requests.get(hard_track_url)
        title_tag = request.text.split("<title>")[1].split("</title")[0]
        track_data["title"] = title_tag.split(" by ")[0].strip()
        track_data["artist"] = title_tag.split(" by ")[1].split("|")[0].strip()
        # TODO: Scrape more data?

        puts_safe(colored.green("Scraping") + colored.white(f": {track_data['title']}"))

        filenames = []
        filename = sanitize_filename(f"{track_data['artist']}  -  {track_data['title']}.mp3")

        if folders:
            name_path = join(vargs["path"], track_data["artist"])
            if not exists(name_path):
                mkdir(name_path)
            filename = join(name_path, filename)
        else:
            filename = join(vargs["path"], filename)

        if exists(filename):
            puts_safe(colored.yellow("Track already downloaded: ") + colored.white(track_data["title"]))
            return None

        filename = download_file(hard_track_url, filename)
        tagged = tag_file(filename, artist=track_data["artist"], title=track_data["title"])

        if not tagged:
            wav_filename = f"{filename[:-3]}wav"
            os.rename(filename, wav_filename)
            filename = wav_filename

        filenames.append(filename)

    # This is is likely a 'likes' page.
    if not hasattr(resolved, "kind"):
        tracks = resolved
    else:
        if resolved.kind == "playlist":
            id3_extras["album"] = resolved.title
            if resolved.tracks != []:
                tracks = resolved.tracks
            else:
                tracks = get_soundcloud_api_playlist_data(resolved.id)["tracks"]
                tracks = tracks[:num_tracks]
                for track in tracks:
                    download_track(track, resolved.title, keep_previews, folders, custom_path=vargs["path"])
                return
        elif resolved.kind == "track":
            tracks = [resolved]
        elif resolved.kind == "group":
            group_id = str(resolved.id)
            tracks = client.get(f"/groups/{group_id}/tracks", limit=200)
        else:
            artist_id = str(resolved.id)
            tracks = client.get(f"/users/{artist_id}/tracks", limit=200)

        # SoundCloud has a unfortunate bug where some artists don't have any tracks returned using:
        #   client.get("/users/" + artist_id + "/tracks", limit=200)
        # There are a number of reports of this issue since late 2019 on StackOverflow.
        # It seems that the common pattern is that if an artist has any tracks marked as private,
        # e.g. the track is not downloadable (only streamable), then SoundCloud won't return any
        # tracks for that artist. The way around this is to refer to the artist's RSS feed. This
        # is in the form of:
        #   http://feeds.soundcloud.com/users/soundcloud:users:<artist_id>/sounds.rss

        if len(tracks) == 0 and resolved.track_count > 0:
            artist = str(resolved.full_name)
            artist_id = str(resolved.id)
            filenames = []

            response = requests.get(f"http://feeds.soundcloud.com/users/soundcloud:users:{artist_id}/sounds.rss")
            if response.status_code != 200:
                # TODO: add error reporting and handling
                return

            feed = atoma.parse_rss_bytes(response.content)
            for feed_item in feed.items:
                filename = download_track_from_feed(artist, feed.image.url, feed_item, folders, vargs["path"])
                if filename is not None:
                    filenames.append(filename)
        else:
            filenames = download_tracks(
                client, tracks, num_tracks, vargs["downloadable"], folders, vargs["path"], id3_extras=id3_extras,
            )

    if vargs["open"]:
        open_files(filenames)


def download_track_from_feed(artist, artwork, track, folders=False, custom_path=""):
    """Given an RSS feed item, download the track."""
    if len(track.enclosures) == 0:
        return None
    url = track.enclosures[0].url
    title = track.title

    filename = sanitize_filename(f"{artist} - {title}.mp3")

    if folders:
        name_path = join(custom_path, artist)
        if not exists(name_path):
            mkdir(name_path)
        filename = join(name_path, filename)
    else:
        filename = join(custom_path, filename)

    if exists(filename):
        puts_safe(colored.yellow("Track already downloaded: ") + colored.white(title))
        return None

    puts_safe(colored.green("Scraping") + colored.white(f": {title}"))

    filename = download_file(url, filename)
    tagged = tag_file(filename, artist=artist, title=title, year=track.pub_date.year, artwork_url=artwork,)
    if not tagged:
        wav_filename = f"{filename[:-3]}wav"
        os.rename(filename, wav_filename)
        filename = wav_filename

    return filename


def download_track(
    track, album_name="", keep_previews=False, folders=False, filenames=[], custom_path="",
):
    """Given a track, force scrape it."""
    hard_track_url = get_hard_track_url(track["id"])

    # We have no info on this track whatsoever.
    if "title" not in track:
        return None

    if not keep_previews:
        if track.get("duration", 0) < track.get("full_duration", 0):
            puts_safe(colored.yellow("Skipping preview track") + colored.white(f": {track['title']}"))
            return None

    # May not have a "full name"
    name = track["user"].get("full_name", "")
    if name == "":
        name = track["user"]["username"]

    filename = sanitize_filename(f"{name}  - {track['title']}.mp3")

    if folders:
        name_path = join(custom_path, name)
        if not exists(name_path):
            mkdir(name_path)
        filename = join(name_path, filename)
    else:
        filename = join(custom_path, filename)

    if exists(filename):
        puts_safe(colored.yellow("Track already downloaded: ") + colored.white(track["title"]))
        return None

    # Skip already downloaded track.
    if filename in filenames:
        return None

    if hard_track_url:
        puts_safe(colored.green("Scraping") + colored.white(f": {track['title']}"))
    else:
        # Region coded?
        puts_safe(colored.yellow("Unable to download") + colored.white(f": {track['title']}"))
        return None

    filename = download_file(hard_track_url, filename)
    tagged = tag_file(
        filename,
        artist=name,
        title=track["title"],
        year=track["created_at"][:4],
        genre=track["genre"],
        album=album_name,
        artwork_url=track["artwork_url"],
    )
    if not tagged:
        wav_filename = f"{filename[:-3]}wav"
        os.rename(filename, wav_filename)
        filename = wav_filename

    return filename


def download_tracks(
    client, tracks, num_tracks=sys.maxsize, downloadable=False, folders=False, custom_path="", id3_extras={},
):
    """Given a list of tracks, iteratively download all of them."""
    filenames = []

    for i, track in enumerate(tracks):
        # "Track" and "Resource" objects are actually different, even though they're the same.
        if isinstance(track, soundcloud.resource.Resource):
            try:
                t_track = {}
                t_track["downloadable"] = track.downloadable
                t_track["streamable"] = track.streamable
                t_track["title"] = track.title
                t_track["user"] = {"username": track.user["username"]}
                t_track["release_year"] = track.release
                t_track["genre"] = track.genre
                t_track["artwork_url"] = track.artwork_url
                if track.downloadable:
                    t_track["stream_url"] = track.download_url
                else:
                    if downloadable:
                        puts_safe(colored.red("Skipping") + colored.white(f": {track.title}"))
                        continue
                    if hasattr(track, "stream_url"):
                        t_track["stream_url"] = track.stream_url
                    else:
                        t_track["direct"] = True
                        streams_url = f"https://api.soundcloud.com/i1/tracks/{track.id}/streams?client_id={AGGRESSIVE_CLIENT_ID}&app_version={APP_VERSION}"
                        response = requests.get(streams_url).json()
                        t_track["stream_url"] = response["http_mp3_128_url"]

                track = t_track
            except:
                puts_safe(colored.white(track.title) + colored.red(" is not downloadable."))
                continue

        if i > num_tracks - 1:
            continue
        try:
            if not track.get("stream_url", False):
                puts_safe(colored.white(track["title"]) + colored.red(" is not downloadable."))
                continue
            else:
                track_artist = sanitize_filename(track["user"]["username"])
                track_title = sanitize_filename(track["title"])
                track_filename = f"{track_artist}  - {track_title}.mp3"

                if folders:
                    track_artist_path = join(custom_path, track_artist)
                    if not exists(track_artist_path):
                        mkdir(track_artist_path)
                    track_filename = join(track_artist_path, track_filename)
                else:
                    track_filename = join(custom_path, track_filename)

                if exists(track_filename):
                    puts_safe(colored.yellow("Track already downloaded: ") + colored.white(track_title))
                    continue

                puts_safe(colored.green("Downloading") + colored.white(f": {track['title']}"))

                if track.get("direct", False):
                    location = track["stream_url"]
                else:
                    stream = client.get(track["stream_url"], allow_redirects=False, limit=200)
                    if hasattr(stream, "location"):
                        location = stream.location
                    else:
                        location = stream.url

                filename = download_file(location, track_filename)
                tagged = tag_file(
                    filename,
                    artist=track["user"]["username"],
                    title=track["title"],
                    year=track["release_year"],
                    genre=track["genre"],
                    album=id3_extras.get("album", None),
                    artwork_url=track["artwork_url"],
                )

                if not tagged:
                    wav_filename = f"{filename[:-3]}wav"
                    os.rename(filename, wav_filename)
                    filename = wav_filename

                filenames.append(filename)
        except Exception as e:
            puts_safe(colored.red("Problem downloading ") + colored.white(track["title"]))
            puts_safe(str(e))

    return filenames


def get_soundcloud_api_playlist_data(playlist_id):
    """Scrape the new API. Returns the parsed JSON response."""
    url = f"https://api.soundcloud.com/playlists/{playlist_id}?representation=full&client_id=02gUJC0hH2ct1EGOcYXQIzRFU91c72Ea&app_version=1467724310"
    response = requests.get(url)
    if response.status_code != 200:
        return None

    return response.json()


def get_hard_track_url(item_id):
    """Hard-scrapes a track."""
    url = f"https://api.soundcloud.com/i1/tracks/{item_id}/streams/?client_id={AGGRESSIVE_CLIENT_ID}&app_version={APP_VERSION}"
    response = requests.get(url)
    if response.status_code != 200:
        return None

    json_response = response.json()
    return json_response["http_mp3_128_url"]


####################################################################
# Bandcamp
####################################################################


def process_bandcamp(vargs):
    """Main BandCamp path."""
    artist_url = vargs["artist_url"]

    if "bandcamp.com" in artist_url or ("://" in artist_url and vargs["bandcamp"]):
        bc_url = artist_url
    else:
        bc_url = f"https://{artist_url}.bandcamp.com/music"

    filenames = scrape_bandcamp_url(
        bc_url, num_tracks=vargs["num_tracks"], folders=vargs["folders"], custom_path=vargs["path"],
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


# Largely borrowed from Ronier's bandcampscrape
def scrape_bandcamp_url(url, num_tracks=sys.maxsize, folders=False, custom_path=""):
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
            filenames.append(scrape_bandcamp_url(album_url, num_tracks, folders, custom_path))
        return filenames

    artist = album_data["artist"]
    album_name = album_data["album_name"]

    if folders:
        if album_name:
            directory = f"{artist} - {album_name}"
        else:
            directory = artist
        directory = sanitize_filename(directory)
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
            if track_number and folders:
                track_filename = f"{track_number} - {track_name}.mp3"
            else:
                track_filename = f"{track_name}.mp3"
            track_filename = sanitize_filename(track_filename)

            if folders:
                path = join(directory, track_filename)
            else:
                path = join(custom_path, sanitize_filename(artist) + " - " + track_filename)

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

        except Exception as e:
            puts_safe(colored.red("Problem downloading ") + colored.white(track_name))
            print(e)
    return filenames


def get_bandcamp_metadata(url):
    """
    Read information from the Bandcamp JavaScript object.

    The method may return a list of URLs (indicating this is probably a "main" page which links to one or more albums),
    or a JSON if we can already parse album/track info from the given url.
    The JSON is "sloppy". The native python JSON parser often can't deal, so we use the more tolerant demjson instead.
    """
    request = requests.get(url)
    try:
        sloppy_json = request.text.split("var TralbumData = ")
        sloppy_json = sloppy_json[1].replace('" + "', "")
        sloppy_json = sloppy_json.replace("'", "'")
        sloppy_json = sloppy_json.split("};")[0] + "};"
        sloppy_json = sloppy_json.replace("};", "}")
        output = demjson.decode(sloppy_json)
    # if the JSON parser failed, we should consider it's a "/music" page,
    # so we generate a list of albums/tracks and return it immediately
    except:
        regex_all_albums = r'<a href="(/(?:album|track)/[^>]+)">'
        all_albums = re.findall(regex_all_albums, request.text, re.MULTILINE)
        album_url_list = list()
        for album in all_albums:
            album_url = re.sub(r"music/?$", "", url) + album
            album_url_list.append(album_url)
        return album_url_list
    # if the JSON parser was successful, use a regex to get all tags
    # from this album/track, join them and set it as the "genre"
    regex_tags = r'<a class="tag" href[^>]+>([^<]+)</a>'
    tags = re.findall(regex_tags, request.text, re.MULTILINE)
    # make sure we treat integers correctly with join()
    # according to http://stackoverflow.com/a/7323861
    # (very unlikely, but better safe than sorry!)
    output["genre"] = " ".join(s for s in tags)
    # make sure we always get the correct album name, even if this is a
    # track URL (unless this track does not belong to any album, in which
    # case the album name remains set as None.
    output["album_name"] = None
    regex_album_name = r'album_title\s*:\s*"([^"]+)"\s*,'
    match = re.search(regex_album_name, request.text, re.MULTILINE)
    if match:
        output["album_name"] = match.group(1)

    try:
        artUrl = request.text.split('"tralbumArt">')[1].split('">')[0].split('href="')[1]
        output["artFullsizeUrl"] = artUrl
    except:
        puts_safe(colored.red("Couldn't get full artwork") + "")
        output["artFullsizeUrl"] = None

    return output


####################################################################
# Mixcloud
####################################################################


def process_mixcloud(vargs):
    """Main MixCloud path."""
    artist_url = vargs["artist_url"]

    if "mixcloud.com" in artist_url:
        mc_url = artist_url
    else:
        mc_url = f"https://mixcloud.com/{artist_url}"

    filenames = scrape_mixcloud_url(
        mc_url, num_tracks=vargs["num_tracks"], folders=vargs["folders"], custom_path=vargs["path"],
    )

    if vargs["open"]:
        open_files(filenames)

    return


def scrape_mixcloud_url(mc_url, num_tracks=sys.maxsize, folders=False, custom_path=""):
    """
    Pull out artist and track info from a MixCloud URL.

    Returns:
        list: filenames to open

    """
    try:
        data = get_mixcloud_data(mc_url)
    except Exception as e:
        puts_safe(colored.red("Problem downloading ") + mc_url)
        print(e)
        return []

    filenames = []

    track_artist = sanitize_filename(data["artist"])
    track_title = sanitize_filename(data["title"])
    track_filename = f"{track_artist} - {track_title}{data['mp3_url'][-4:]}"

    if folders:
        track_artist_path = join(custom_path, track_artist)
        if not exists(track_artist_path):
            mkdir(track_artist_path)
        track_filename = join(track_artist_path, track_filename)
        if exists(track_filename):
            puts_safe(colored.yellow("Skipping") + colored.white(f": {data['title']} - already exists!"))
            return []
    else:
        track_filename = join(custom_path, track_filename)

    puts_safe(colored.green("Downloading") + colored.white(f": {data['artist']} - {data['title']} ({track_filename[-4:]})"))
    download_file(data["mp3_url"], track_filename)
    if track_filename[-4:] == ".mp3":
        tag_file(
            track_filename,
            artist=data["artist"],
            title=data["title"],
            year=data["year"],
            genre="Mix",
            artwork_url=data["artwork_url"],
        )
    filenames.append(track_filename)

    return filenames


def get_mixcloud_data(url):
    """
    Scrapes a Mixcloud page for a track's important information.

    Returns:
        dict: containing audio data

    """
    data = {}
    request = requests.get(url)
    preview_mp3_url = request.text.split('m-preview="')[1].split('" m-preview-light')[0]
    song_uuid = preview_mp3_url.split("previews/")[1].split(".mp3")[0]

    # Fish for the m4a.
    for server in range(1, 23):
        # Ex: https://stream6.mixcloud.com/c/m4a/64/1/2/0/9/30fe-23aa-40da-9bf3-4bee2fba649d.m4a
        mp3_url = f"https://stream{server}.mixcloud.com/c/m4a/64/{song_uuid}.m4a"
        try:
            if requests.head(mp3_url).status_code == 200:
                if "?" in mp3_url:
                    mp3_url = mp3_url.split("?")[0]
                break
        except:
            continue

    full_title = request.text.split("<title>")[1].split(" | Mixcloud")[0]
    title = full_title.split(" by ")[0].strip()
    artist = full_title.split(" by ")[1].strip()

    img_thumbnail_url = request.text.split('m-thumbnail-url="')[1].split(" ng-class")[0]
    artwork_url = img_thumbnail_url.replace("60/", "300/").replace("60/", "300/").replace("//", "https://").replace('"', "")

    data["mp3_url"] = mp3_url
    data["title"] = title
    data["artist"] = artist
    data["artwork_url"] = artwork_url
    data["year"] = None

    return data


####################################################################
# Audiomack
####################################################################


def process_audiomack(vargs):
    """Main Audiomack path."""
    artist_url = vargs["artist_url"]

    if "audiomack.com" in artist_url:
        mc_url = artist_url
    else:
        mc_url = f"https://audiomack.com/{artist_url}"

    filenames = scrape_audiomack_url(
        mc_url, num_tracks=vargs["num_tracks"], folders=vargs["folders"], custom_path=vargs["path"],
    )

    if vargs["open"]:
        open_files(filenames)


def scrape_audiomack_url(mc_url, num_tracks=sys.maxsize, folders=False, custom_path=""):
    """
    Pull out artist and track info from a Audiomack URL.

    Returns:
        list: filenames to open

    """
    try:
        data = get_audiomack_data(mc_url)
    except Exception as e:
        puts_safe(colored.red("Problem downloading ") + mc_url)
        print(e)

    filenames = []

    track_artist = sanitize_filename(data["artist"])
    track_title = sanitize_filename(data["title"])
    track_filename = f"{track_artist} - {track_title}.mp3"

    if folders:
        track_artist_path = join(custom_path, track_artist)
        if not exists(track_artist_path):
            mkdir(track_artist_path)
        track_filename = join(track_artist_path, track_filename)
        if exists(track_filename):
            puts_safe(colored.yellow("Skipping") + colored.white(f": {data['title']} - already exists!"))
            return []
    else:
        track_filename = join(custom_path, track_filename)

    puts_safe(colored.green("Downloading") + colored.white(f": {data['artist']} - {data['title']}"))
    download_file(data["mp3_url"], track_filename)
    tag_file(
        track_filename,
        artist=data["artist"],
        title=data["title"],
        year=data["year"],
        genre=None,
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
    data = {}
    request = requests.get(url)

    mp3_url = request.text.split('class="player-icon download-song" title="Download" href="')[1].split('"')[0]
    artist = request.text.split('<span class="artist">')[1].split("</span>")[0].strip()
    title = request.text.split('<span class="artist">')[1].split("</span>")[1].split("</h1>")[0].strip()
    artwork_url = request.text.split('<a class="lightbox-trigger" href="')[1].split('" data')[0].strip()

    data["mp3_url"] = mp3_url
    data["title"] = title
    data["artist"] = artist
    data["artwork_url"] = artwork_url
    data["year"] = None

    return data


####################################################################
# MusicBed
####################################################################


def process_musicbed(vargs):
    """Main MusicBed path."""
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
        folders=vargs["folders"],
        custom_path=vargs["path"],
    )

    if vargs["open"]:
        open_files(filenames)


def scrape_musicbed_url(url, login, password, num_tracks=sys.maxsize, folders=False, custom_path=""):
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
        puts(
            colored.red("scrape_musicbed_url: couldn't login. Aborting. ")
            + colored.white("Did you provide correct login and password?")
        )
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
                if folders:
                    sanitized_artist = sanitize_filename(each_song["album"]["data"]["artist"]["data"]["name"])
                    sanitized_album = sanitize_filename(each_song["album"]["data"]["name"])
                    directory = join(directory, sanitized_artist + " - " + sanitized_album)
                    if not exists(directory):
                        mkdir(directory)
                filename = join(directory, str(song_count) + " - " + sanitize_filename(each_song["name"]) + ".mp3",)

                if exists(filename):
                    puts_safe(colored.yellow("Skipping") + colored.white(f": {each_song['name']} - already exists!"))
                    song_count += 1
                    continue

                puts_safe(colored.green("Downloading") + colored.white(f": {each_song['name']}"))
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

    if session and params:
        r = session.get(url, params=params, stream=True)
    elif session and not params:
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
    try:
        audio = EasyMP3(filename)
        audio.tags = None
        audio["artist"] = artist
        audio["title"] = title
        if year:
            audio["date"] = str(year)
        if album:
            audio["album"] = album
        if track_number:
            audio["tracknumber"] = track_number
        if genre:
            audio["genre"] = genre
        if url:  # saves the tag as WOAR
            audio["website"] = url
        audio.save()

        if artwork_url:
            artwork_url = artwork_url.replace("https", "http")

            mime = "image/jpeg"
            if ".jpg" in artwork_url:
                mime = "image/jpeg"
            if ".png" in artwork_url:
                mime = "image/png"

            if "-large" in artwork_url:
                new_artwork_url = artwork_url.replace("-large", "-t500x500")
                try:
                    image_data = requests.get(new_artwork_url).content
                except:
                    # No very large image available.
                    image_data = requests.get(artwork_url).content
            else:
                image_data = requests.get(artwork_url).content

            audio = MP3(filename, ID3=OldID3)

            # encoding=3 means utf-8
            # type=3 means cover image
            audio.tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=image_data))
            audio.save()

        # because there is software that doesn't seem to use WOAR we save url tag again as WXXX
        if url:
            audio = MP3(filename, ID3=OldID3)
            audio.tags.add(WXXX(encoding=3, url=url))
            audio.save()

        return True

    except:
        puts(colored.red("Problem tagging file: ") + colored.white("Is this file a WAV?"))
        return False


def open_files(filenames):
    """Call the system 'open' command on a file."""
    command = ["open"] + filenames
    process = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()


def sanitize_filename(filename):
    """
    Make sure filenames are valid paths.

    Returns:
        str:

    """
    sanitized_filename = re.sub(r'[/\\:*?"<>|]', "-", filename)
    sanitized_filename = sanitized_filename.replace("&", "and")
    sanitized_filename = sanitized_filename.replace('"', "")
    sanitized_filename = sanitized_filename.replace("'", "")
    sanitized_filename = sanitized_filename.replace("/", "")
    sanitized_filename = sanitized_filename.replace("\\", "")

    # Annoying.
    if sanitized_filename[0] == ".":
        sanitized_filename = f"dot{sanitized_filename[1:]}"

    return sanitized_filename


def puts_safe(text):
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
