#! /usr/bin/env python
from __future__ import unicode_literals

import argparse
import demjson
import os
import re
import requests
import soundcloud
import sys

from clint.textui import colored, puts, progress
from datetime import datetime
from mutagen.mp3 import MP3, EasyMP3
from mutagen.id3 import APIC
from mutagen.id3 import ID3 as OldID3
from subprocess import Popen, PIPE
from os.path import exists, join
from os import mkdir

####################################################################

# Please be nice with this!
CLIENT_ID = '175c043157ffae2c6d5fed16c3d95a4c'
CLIENT_SECRET = '99a51990bd81b6a82c901d4cc6828e46'
MAGIC_CLIENT_ID = 'b45b1aa10f1ac2941910a7f0d10f8e28'

AGGRESSIVE_CLIENT_ID = '02gUJC0hH2ct1EGOcYXQIzRFU91c72Ea'
APP_VERSION = '1464790339'

####################################################################


def main():
    """
    Main function.

    Converts arguments to Python and processes accordingly.

    """

    # Hack related to #58
    if sys.platform == "win32": 
        os.system("chcp 65001");

    parser = argparse.ArgumentParser(description='SoundScrape. Scrape an artist from SoundCloud.\n')
    parser.add_argument('artist_url', metavar='U', type=str, nargs='*',
                        help='An artist\'s SoundCloud username or URL')
    parser.add_argument('-n', '--num-tracks', type=int, default=sys.maxsize,
                        help='The number of tracks to download')
    parser.add_argument('-g', '--group', action='store_true',
                        help='Use if downloading tracks from a SoundCloud group')
    parser.add_argument('-b', '--bandcamp', action='store_true',
                        help='Use if downloading from Bandcamp rather than SoundCloud')
    parser.add_argument('-m', '--mixcloud', action='store_true',
                        help='Use if downloading from Mixcloud rather than SoundCloud')
    parser.add_argument('-a', '--audiomack', action='store_true',
                        help='Use if downloading from Audiomack rather than SoundCloud')
    parser.add_argument('-c', '--hive', action='store_true',
                        help='Use if downloading from Hive.co rather than SoundCloud')
    parser.add_argument('-l', '--likes', action='store_true',
                        help='Download all of a user\'s Likes.')
    parser.add_argument('-d', '--downloadable', action='store_true',
                        help='Only fetch traks with a Downloadable link.')
    parser.add_argument('-t', '--track', type=str, default='',
                        help='The name of a specific track by an artist')
    parser.add_argument('-f', '--folders', action='store_true',
                        help='Organize saved songs in folders by artists')
    parser.add_argument('-o', '--open', action='store_true',
                        help='Open downloaded files after downloading.')
    parser.add_argument('-k', '--keep', action='store_true',
                        help='Keep 30-second preview tracks')
    parser.add_argument('-v', '--version', action='store_true', default=False,
                        help='Display the current version of SoundScrape')

    args = parser.parse_args()
    vargs = vars(args)

    if vargs['version']:
        import pkg_resources
        version = pkg_resources.require("soundscrape")[0].version
        print(version)
        return

    if not vargs['artist_url']:
        parser.error('Please supply an artist\'s username or URL!')

    vargs['artist_url'] = vargs['artist_url'][0]
    artist_url = vargs['artist_url']

    if 'bandcamp.com' in artist_url or vargs['bandcamp']:
        process_bandcamp(vargs)
    elif 'mixcloud.com' in artist_url or vargs['mixcloud']:
        process_mixcloud(vargs)
    elif 'audiomack.com' in artist_url or vargs['audiomack']:
        process_audiomack(vargs)
    elif 'hive.co' in artist_url or vargs['hive']:
        process_hive(vargs)
    else:
        process_soundcloud(vargs)


####################################################################
# SoundCloud
####################################################################


def process_soundcloud(vargs):
    """
    Main SoundCloud path.
    """

    artist_url = vargs['artist_url']
    track_permalink = vargs['track']
    keep_previews = vargs['keep']
    folders = vargs['folders']

    id3_extras = {}
    one_track = False
    likes = False
    client = get_client()
    if 'soundcloud' not in artist_url.lower():
        if vargs['group']:
            artist_url = 'https://soundcloud.com/groups/' + artist_url.lower()
        elif len(track_permalink) > 0:
            one_track = True
            track_url = 'https://soundcloud.com/' + artist_url.lower() + '/' + track_permalink.lower()
        else:
            artist_url = 'https://soundcloud.com/' + artist_url.lower()
            if vargs['likes'] or 'likes' in artist_url.lower():
                likes = True
    if 'likes' in artist_url.lower():
        artist_url = artist_url[0:artist_url.find('/likes')]

    if one_track:
        num_tracks = 1
    else:
        num_tracks = vargs['num_tracks']

    try:
        if one_track:
            resolved = client.get('/resolve', url=track_url, limit=200)

        elif likes:
            userId = str(client.get('/resolve', url=artist_url).id)
            resolved = client.get('/users/' + userId + '/favorites', limit=200)
        else:
            resolved = client.get('/resolve', url=artist_url, limit=200)

    except Exception as e:  # HTTPError?

        # SoundScrape is trying to prevent us from downloading this.
        # We're going to have to stop trusting the API/client and 
        # do all our own scraping. Boo.

        message = str(e)
        item_id = message.rsplit('/', 1)[-1].split('.json')[0].split('?client_id')[0]
        hard_track_url = get_hard_track_url(item_id)

        track_data = get_soundcloud_data(artist_url)
        puts(colored.green("Scraping") + colored.white(": " + track_data['title']))

        filenames = []
        filename = sanitize_filename(track_data['artist'] + ' - ' + track_data['title'] + '.mp3')

        if folders:
            name = track_data['artist']
            if not exists(name):
                mkdir(name)
            filename = join(name, filename)

        if exists(filename) and folders:
            puts(colored.yellow("Track already downloaded: ") + colored.white(track_data['title']))
            return None

        filename = download_file(hard_track_url, filename)
        tag_file(filename,
                 artist=track_data['artist'],
                 title=track_data['title'],
                 year='2016',
                 genre='',
                 album='',
                 artwork_url='')

        filenames.append(filename)

    else:
        aggressive = False

        # This is is likely a 'likes' page.
        if not hasattr(resolved, 'kind'):
            tracks = resolved
        else:
            if resolved.kind == 'artist':
                artist = resolved
                artist_id = str(artist.id)
                tracks = client.get('/users/' + artist_id + '/tracks', limit=200)
            elif resolved.kind == 'playlist':
                tracks = resolved.tracks
                id3_extras['album'] = resolved.title
            elif resolved.kind == 'track':
                tracks = [resolved]
            elif resolved.kind == 'group':
                group = resolved
                group_id = str(group.id)
                tracks = client.get('/groups/' + group_id + '/tracks', limit=200)
            else:
                artist = resolved
                artist_id = str(artist.id)
                tracks = client.get('/users/' + artist_id + '/tracks', limit=200)
                if tracks == [] and artist.track_count > 0:
                    aggressive = True
                    filenames = []

                    data = get_soundcloud_api2_data(artist_id)

                    def download_track(track, album_name=u''):
    
                        hard_track_url = get_hard_track_url(track['id'])

                        # We have no info on this track whatsoever.
                        if not 'title' in track:
                            return None

                        if not keep_previews:
                            if (track.get('duration', 0) < track.get('full_duration', 0)):
                                puts(colored.yellow("Skipping preview track") + colored.white(": " + track['title']))
                                return None

                        # May not have a "full name"
                        name = track['user']['full_name']
                        if name == '':
                            name = track['user']['username']

                        filename = sanitize_filename(name + ' - ' + track['title'] + '.mp3')

                        if folders:
                            if not exists(name):
                                mkdir(name)
                            filename = join(name, filename)

                        if exists(filename) and folders:
                            puts(colored.yellow("Track already downloaded: ") + colored.white(track['title']))

                            return None

                        # Skip already downloaded track.
                        if filename in filenames:
                            return None

                        if hard_track_url:
                            puts(colored.green("Scraping") + colored.white(": " + track['title']))
                        else:
                            # Region coded?
                            puts(colored.yellow("Unable to download") + colored.white(": " + track['title']))
                            return None

                        filename = download_file(hard_track_url, filename)
                        tag_file(filename,
                                 artist=name,
                                 title=track['title'],
                                 year=track['created_at'][:4],
                                 genre=track['genre'],
                                 album=album_name,
                                 artwork_url=track['artwork_url'])

                        return filename

                    for track in data['collection']:

                        if len(filenames) >= num_tracks:
                            break

                        if track['type'] == 'playlist':
                            for playlist_track in track['playlist']['tracks']:
                                album_name = track['playlist']['title']
                                filename = download_track(playlist_track, album_name)
                                if filename:
                                    filenames.append(filename)
                        else:
                            d_track = track['track']
                            filename = download_track(d_track)
                            if filename:
                                filenames.append(filename)

        if not aggressive:
            filenames = download_tracks(client, tracks, num_tracks, vargs['downloadable'], vargs['folders'],
                                        id3_extras=id3_extras)

    if vargs['open']:
        open_files(filenames)


def get_client():
    """
    Return a new SoundCloud Client object.
    """
    client = soundcloud.Client(client_id=CLIENT_ID)
    return client


def download_tracks(client, tracks, num_tracks=sys.maxsize, downloadable=False, folders=False, id3_extras={}):
    """
    Given a list of tracks, iteratively download all of them.

    """

    filenames = []

    for i, track in enumerate(tracks):

        # "Track" and "Resource" objects are actually different,
        # even though they're the same.
        if isinstance(track, soundcloud.resource.Resource):

            try:

                t_track = {}
                t_track['downloadable'] = track.downloadable
                t_track['streamable'] = track.streamable
                t_track['title'] = track.title
                t_track['user'] = {'username': track.user['username']}
                t_track['release_year'] = track.release
                t_track['genre'] = track.genre
                t_track['artwork_url'] = track.artwork_url
                if track.downloadable:
                    t_track['stream_url'] = track.download_url
                else:
                    if downloadable:
                        puts(colored.red("Skipping") + colored.white(": " + track.title))
                        continue
                    if hasattr(track, 'stream_url'):
                        t_track['stream_url'] = track.stream_url
                    else:
                        t_track['direct'] = True
                        streams_url = "https://api.soundcloud.com/i1/tracks/%s/streams?client_id=%s&app_version=%s" % (
                        str(track.id), AGGRESSIVE_CLIENT_ID, APP_VERSION)
                        response = requests.get(streams_url).json()
                        t_track['stream_url'] = response['http_mp3_128_url']

                track = t_track
            except Exception as e:
                puts(colored.white(track.title) + colored.red(' is not downloadable.'))
                print(e)
                continue

        if i > num_tracks - 1:
            continue
        try:
            if not track.get('stream_url', False):
                puts(colored.white(track['title']) + colored.red(' is not downloadable.'))
                continue
            else:
                track_artist = sanitize_filename(track['user']['username'])
                track_title = sanitize_filename(track['title'])
                track_filename = track_artist + ' - ' + track_title + '.mp3'

                if folders:
                    if not exists(track_artist):
                        mkdir(track_artist)
                    track_filename = join(track_artist, track_filename)

                if exists(track_filename) and folders:
                    puts(colored.yellow("Track already downloaded: ") + colored.white(track_title))
                    continue

                puts(colored.green("Downloading") + colored.white(": " + track['title']))
                if track.get('direct', False):
                    location = track['stream_url']
                else:
                    stream = client.get(track['stream_url'], allow_redirects=False, limit=200)
                    if hasattr(stream, 'location'):
                        location = stream.location
                    else:
                        location = stream.url

                path = download_file(location, track_filename)
                tag_file(path,
                         artist=track['user']['username'],
                         title=track['title'],
                         year=track['release_year'],
                         genre=track['genre'],
                         album=id3_extras.get('album', None),
                         artwork_url=track['artwork_url'])
                filenames.append(path)
        except Exception as e:
            puts(colored.red("Problem downloading ") + colored.white(track['title']))
            print(e)

    return filenames


def get_soundcloud_data(url):
    """
    Scrapes a SoundCloud page for a track's important information.

    Returns:
        dict: of audio data

    """

    data = {}

    request = requests.get(url)

    title_tag = request.text.split('<title>')[1].split('</title')[0]
    data['title'] = title_tag.split(' by ')[0].strip()
    data['artist'] = title_tag.split(' by ')[1].split('|')[0].strip()
    # XXX Do more..

    return data


def get_soundcloud_api2_data(artist_id):
    """
    Scrape the new API. Returns the parsed JSON response.
    """

    v2_url = "https://api-v2.soundcloud.com/stream/users/%s?limit=500&client_id=%s&app_version=%s" % (
    artist_id, AGGRESSIVE_CLIENT_ID, APP_VERSION)
    response = requests.get(v2_url)
    parsed = response.json()

    return parsed


def get_hard_track_url(item_id):
    """
    Hard-scrapes a track.
    """

    streams_url = "https://api.soundcloud.com/i1/tracks/%s/streams/?client_id=%s&app_version=%s" % (
    item_id, AGGRESSIVE_CLIENT_ID, APP_VERSION)
    response = requests.get(streams_url)
    json_response = response.json()

    if response.status_code == 200:
        hard_track_url = json_response['http_mp3_128_url']
        return hard_track_url
    else:
        return None

####################################################################
# Bandcamp
####################################################################


def process_bandcamp(vargs):
    """
    Main BandCamp path.
    """

    artist_url = vargs['artist_url']

    if 'bandcamp.com' in artist_url or ('://' in artist_url and vargs['bandcamp']):
        bc_url = artist_url
    else:
        bc_url = 'https://' + artist_url + '.bandcamp.com/music'

    filenames = scrape_bandcamp_url(bc_url, num_tracks=vargs['num_tracks'], folders=vargs['folders'])

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

    if vargs['open']:
        open_files(filenames)

    return


# Largely borrowed from Ronier's bandcampscrape
def scrape_bandcamp_url(url, num_tracks=sys.maxsize, folders=False):
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
            filenames.append(scrape_bandcamp_url(album_url, num_tracks, folders))
        return filenames

    artist = album_data["artist"]
    album_name = album_data["album_name"]

    if folders:
        if album_name:
            directory = artist + " - " + album_name
        else:
            directory = artist
        directory = sanitize_filename(directory)
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
                track_filename = '%s - %s.mp3' % (track_number, track_name)
            else:
                track_filename = '%s.mp3' % (track_name)
            track_filename = sanitize_filename(track_filename)
            if folders:
                path = join(directory, track_filename)
            else:
                path = artist + ' - ' + track_filename
            if exists(path):
                puts(colored.yellow("Track already downloaded: ") + colored.white(track_name))
                continue

            if not track['file']:
                puts(colored.yellow("Track unavailble for scraping: ") + colored.white(track_name))
                continue

            puts(colored.green("Downloading") + colored.white(": " + track_name))
            path = download_file(track['file']['mp3-128'], path)

            album_year = album_data['album_release_date']
            if album_year:
                album_year = datetime.strptime(album_year, "%d %b %Y %H:%M:%S GMT").year

            tag_file(path,
                     artist,
                     track_name,
                     album=album_name,
                     year=album_year,
                     genre=album_data['genre'],
                     artwork_url=album_data['artFullsizeUrl'],
                     track_number=track_number)

            filenames.append(path)

        except Exception as e:
            puts(colored.red("Problem downloading ") + colored.white(track_name))
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
        sloppy_json = sloppy_json.replace("'", "\'")
        sloppy_json = sloppy_json.split("};")[0] + "};"
        sloppy_json = sloppy_json.replace("};", "}")
        output = demjson.decode(sloppy_json)
    # if the JSON parser failed, we should consider it's a "/music" page,
    # so we generate a list of albums/tracks and return it immediately
    except Exception as e:
        regex_all_albums = r'<a href="(/(?:album|track)/[^>]+)">'
        all_albums = re.findall(regex_all_albums, request.text, re.MULTILINE)
        album_url_list = list()
        for album in all_albums:
            album_url = re.sub(r'music/?$', '', url) + album
            album_url_list.append(album_url)
        return album_url_list
    # if the JSON parser was successful, use a regex to get all tags
    # from this album/track, join them and set it as the "genre"
    regex_tags = r'<a class="tag" href[^>]+>([^<]+)</a>'
    tags = re.findall(regex_tags, request.text, re.MULTILINE)
    # make sure we treat integers correctly with join()
    # according to http://stackoverflow.com/a/7323861
    # (very unlikely, but better safe than sorry!)
    output['genre'] = ' '.join(s for s in tags)
    # make sure we always get the correct album name, even if this is a
    # track URL (unless this track does not belong to any album, in which
    # case the album name remains set as None.
    output['album_name'] = None
    regex_album_name = r'album_title\s*:\s*"([^"]+)"\s*,'
    match = re.search(regex_album_name, request.text, re.MULTILINE)
    if match:
        output['album_name'] = match.group(1)
    return output


####################################################################
# Mixcloud
####################################################################


def process_mixcloud(vargs):
    """
    Main MixCloud path.
    """

    artist_url = vargs['artist_url']

    if 'mixcloud.com' in artist_url:
        mc_url = artist_url
    else:
        mc_url = 'https://mixcloud.com/' + artist_url

    filenames = scrape_mixcloud_url(mc_url, num_tracks=vargs['num_tracks'], folders=vargs['folders'])

    if vargs['open']:
        open_files(filenames)

    return


def scrape_mixcloud_url(mc_url, num_tracks=sys.maxsize, folders=False):
    """
    Returns:
        list: filenames to open

    """

    try:
        data = get_mixcloud_data(mc_url)
    except Exception as e:
        puts(colored.red("Problem downloading ") + mc_url)
        print(e)
        return []

    filenames = []

    track_artist = sanitize_filename(data['artist'])
    track_title = sanitize_filename(data['title'])
    track_filename = track_artist + ' - ' + track_title + data['mp3_url'][-4:]

    if folders:
        if not exists(track_artist):
            mkdir(track_artist)
        track_filename = join(track_artist, track_filename)
        if exists(track_filename):
            puts(colored.yellow("Skipping") + colored.white(': ' + data['title'] + " - it already exists!"))
            return []

    puts(colored.green("Downloading") + colored.white(
        ': ' + data['artist'] + " - " + data['title'] + " (" + track_filename[-4:] + ")"))
    download_file(data['mp3_url'], track_filename)
    if track_filename[-4:] == '.mp3':
        tag_file(track_filename,
                 artist=data['artist'],
                 title=data['title'],
                 year=data['year'],
                 genre="Mix",
                 artwork_url=data['artwork_url'])
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
    waveform_server = "https://waveform.mixcloud.com"

    waveform_url = request.text.split('m-waveform="')[1].split('"')[0]
    stream_server = \
    request.text.split('m-p-ref="cloudcast_page" m-play-info="')[1].split('" m-preview="')[1].split('.mixcloud.com')[0]

    # Iterate to fish for the original mp3 stream..
    stream_server = "https://stream"
    m4a_url = waveform_url.replace(waveform_server, stream_server + ".mixcloud.com/c/m4a/64/").replace('.json', '.m4a')
    for server in range(14, 23):
        m4a_url = waveform_url.replace(waveform_server,
                                       stream_server + str(server) + ".mixcloud.com/c/m4a/64/").replace('.json', '.m4a')
        mp3_url = m4a_url.replace('m4a/64', 'originals').replace('.m4a', '.mp3').replace('originals/', 'originals')
        if requests.head(mp3_url).status_code == 200:
            break
        else:
            mp3_url = None

    # .. else fallback to an m4a.
    if not mp3_url:
        m4a_url = waveform_url.replace(waveform_server, stream_server + ".mixcloud.com/c/m4a/64/").replace('.json',
                                                                                                           '.m4a')
        for server in range(14, 23):
            mp3_url = waveform_url.replace(waveform_server,
                                           stream_server + str(server) + ".mixcloud.com/c/m4a/64/").replace('.json',
                                                                                                            '.m4a')
            if requests.head(mp3_url).status_code == 200:
                if '?' in mp3_url:
                    mp3_url = mp3_url.split('?')[0]
                break

    full_title = request.text.split("<title>")[1].split(" | Mixcloud")[0]
    title = full_title.split(' by ')[0].strip()
    artist = full_title.split(' by ')[1].strip()

    img_thumbnail_url = request.text.split('m-thumbnail-url="')[1].split(" ng-class")[0]
    artwork_url = img_thumbnail_url.replace('60/', '300/').replace('60/', '300/').replace('//', 'https://').replace('"',
                                                                                                                    '')

    data['mp3_url'] = mp3_url
    data['title'] = title
    data['artist'] = artist
    data['artwork_url'] = artwork_url
    data['year'] = None

    return data


####################################################################
# Audiomack
####################################################################


def process_audiomack(vargs):
    """
    Main Audiomack path.
    """

    artist_url = vargs['artist_url']

    if 'audiomack.com' in artist_url:
        mc_url = artist_url
    else:
        mc_url = 'https://audiomack.com/' + artist_url

    filenames = scrape_audiomack_url(mc_url, num_tracks=vargs['num_tracks'], folders=vargs['folders'])

    if vargs['open']:
        open_files(filenames)

    return


def scrape_audiomack_url(mc_url, num_tracks=sys.maxsize, folders=False):
    """
    Returns:
        list: filenames to open

    """

    try:
        data = get_audiomack_data(mc_url)
    except Exception as e:
        puts(colored.red("Problem downloading ") + mc_url)
        print(e)

    filenames = []

    track_artist = sanitize_filename(data['artist'])
    track_title = sanitize_filename(data['title'])
    track_filename = track_artist + ' - ' + track_title + '.mp3'

    if folders:
        if not exists(track_artist):
            mkdir(track_artist)
        track_filename = join(track_artist, track_filename)
        if exists(track_filename):
            puts(colored.yellow("Skipping") + colored.white(': ' + data['title'] + " - it already exists!"))
            return []

    puts(colored.green("Downloading") + colored.white(': ' + data['artist'] + " - " + data['title']))
    download_file(data['mp3_url'], track_filename)
    tag_file(track_filename,
             artist=data['artist'],
             title=data['title'],
             year=data['year'],
             genre=None,
             artwork_url=data['artwork_url'])
    filenames.append(track_filename)

    return filenames


def get_audiomack_data(url):
    """
    Scrapes a Mixcloud page for a track's important information.

    Returns:
        dict: containing audio data

    """

    data = {}
    request = requests.get(url)

    mp3_url = request.text.split('class="player-icon download-song" title="Download" href="')[1].split('"')[0]
    artist = request.text.split('<span class="artist">')[1].split('</span>')[0].strip()
    title = request.text.split('<span class="artist">')[1].split('</span>')[1].split('</h1>')[0].strip()
    artwork_url = request.text.split('<a class="lightbox-trigger" href="')[1].split('" data')[0].strip()

    data['mp3_url'] = mp3_url
    data['title'] = title
    data['artist'] = artist
    data['artwork_url'] = artwork_url
    data['year'] = None

    return data


####################################################################
# Hive.co
####################################################################


def process_hive(vargs):
    """
    Main Hive.co path.
    """

    artist_url = vargs['artist_url']

    if 'hive.co' in artist_url:
        mc_url = artist_url
    else:
        mc_url = 'https://www.hive.co/downloads/download/' + artist_url

    filenames = scrape_hive_url(mc_url, num_tracks=vargs['num_tracks'], folders=vargs['folders'])

    if vargs['open']:
        open_files(filenames)

    return


def scrape_hive_url(mc_url, num_tracks=sys.maxsize, folders=False):
    """
    Scrape a Hive.co download page.

    Returns:
        list: filenames to open

    """

    try:
        data = get_hive_data(mc_url)
    except Exception as e:
        puts(colored.red("Problem downloading ") + mc_url)
        print(e)

    filenames = []

    # track_artist = sanitize_filename(data['artist'])
    # track_title = sanitize_filename(data['title'])
    # track_filename = track_artist + ' - ' + track_title + '.mp3'

    # if folders:
    #     if not exists(track_artist):
    #         mkdir(track_artist)
    #     track_filename = join(track_artist, track_filename)
    #     if exists(track_filename):
    #         puts(colored.yellow("Skipping") + colored.white(': ' + data['title'] + " - it already exists!"))
    #         return []

    # puts(colored.green("Downloading") + colored.white(': ' + data['artist'] + " - " + data['title']))
    # download_file(data['mp3_url'], track_filename)
    # tag_file(track_filename,
    #         artist=data['artist'],
    #         title=data['title'],
    #         year=data['year'],
    #         genre=None,
    #         artwork_url=data['artwork_url'])
    # filenames.append(track_filename)

    return filenames


def get_hive_data(url):
    """

    Scrapes a Mixcloud page for a track's important information.

    Returns a dict of data.

    """

    data = {}
    request = requests.get(url)

    # import pdb
    # pdb.set_trace()

    # mp3_url = request.text.split('class="player-icon download-song" title="Download" href="')[1].split('"')[0]
    # artist = request.text.split('<span class="artist">')[1].split('</span>')[0].strip()
    # title = request.text.split('<span class="artist">')[1].split('</span>')[1].split('</h1>')[0].strip()
    # artwork_url = request.text.split('<a class="lightbox-trigger" href="')[1].split('" data')[0].strip()

    # data['mp3_url'] = mp3_url
    # data['title'] = title
    # data['artist'] = artist
    # data['artwork_url'] = artwork_url
    # data['year'] = None

    return data


####################################################################
# File Utility
####################################################################


def download_file(url, path):
    """
    Download an individual file.
    """

    if url[0:2] == '//':
        url = 'https://' + url[2:]

    # Use a temporary file so that we don't import incomplete files.
    tmp_path = path + '.tmp'

    r = requests.get(url, stream=True)
    with open(tmp_path, 'wb') as f:
        total_length = int(r.headers.get('content-length', 0))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length / 1024) + 1):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()

    os.rename(tmp_path, path)

    return path


def tag_file(filename, artist, title, year=None, genre=None, artwork_url=None, album=None, track_number=None):
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
    """

    try:
        audio = EasyMP3(filename)
        audio.tags = None
        audio["artist"] = artist
        audio["title"] = title
        if year:
            audio["date"] = str(str(year).encode('ascii','ignore'))
        if album:
            audio["album"] = album
        if track_number:
            audio["tracknumber"] = track_number
        if genre:
            audio["genre"] = genre
        audio.save()

        if artwork_url:

            artwork_url = artwork_url.replace('https', 'http')

            mime = 'image/jpeg'
            if '.jpg' in artwork_url:
                mime = 'image/jpeg'
            if '.png' in artwork_url:
                mime = 'image/png'

            if '-large' in artwork_url:
                new_artwork_url = artwork_url.replace('-large', '-t500x500')
                try:
                    image_data = requests.get(new_artwork_url).content
                except Exception as e:
                    # No very large image available.
                    image_data = requests.get(artwork_url).content
            else:
                image_data = requests.get(artwork_url).content

            audio = MP3(filename, ID3=OldID3)
            audio.tags.add(
                APIC(
                    encoding=3,  # 3 is for utf-8
                    mime=mime,
                    type=3,  # 3 is for the cover image
                    desc='Cover',
                    data=image_data
                )
            )
            audio.save()
    except Exception as e:
        print(e)


def open_files(filenames):
    """
    Call the system 'open' command on a file.
    """
    command = ['open'] + filenames
    process = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()


def sanitize_filename(filename):
    """
    Make sure filenames are valid paths.

    Returns:
        str: 
    """
    sanitized_filename = re.sub(r'[/\\:*?"<>|]', '-', filename)
    sanitized_filename = sanitized_filename.replace('&', 'and')
    sanitized_filename = sanitized_filename.replace('"', '')
    sanitized_filename = sanitized_filename.replace("'", '')
    return sanitized_filename


####################################################################
# Main
####################################################################

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(e)
