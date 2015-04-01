#! /usr/bin/env python

import soundcloud
import requests
import sys
import argparse
import demjson
from datetime import datetime
from os.path import exists
from os import mkdir
from subprocess import Popen, PIPE

from mutagen.mp3 import MP3, EasyMP3
from mutagen.id3 import APIC
from mutagen.id3 import ID3 as OldID3

from clint.textui import colored, puts, progress

# Please be nice with this!
CLIENT_ID = '22e566527758690e6feb2b5cb300cc43'
CLIENT_SECRET = '3a7815c3f9a82c3448ee4e7d3aa484a4'
MAGIC_CLIENT_ID = 'b45b1aa10f1ac2941910a7f0d10f8e28'


def main():
    parser = argparse.ArgumentParser(description='SoundScrape. Scrape an artist from SoundCloud.\n')
    parser.add_argument('artist_url', metavar='U', type=str,
                   help='An artist\'s SoundCloud username or URL')
    parser.add_argument('-n', '--num-tracks', type=int, default=sys.maxint,
                        help='The number of tracks to download')
    parser.add_argument('-g', '--group', action='store_true',
                        help='Use if downloading tracks from a SoundCloud group')
    parser.add_argument('-b', '--bandcamp', action='store_true',
                        help='Use if downloading from Bandcamp rather than SoundCloud')
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

    args = parser.parse_args()
    vargs = vars(args)
    if not any(vargs.values()):
        parser.error('Please supply an artist\'s username or URL!')

    artist_url = vargs['artist_url']
    track_permalink = vargs['track']
    one_track = False

    if 'bandcamp.com' in artist_url or vargs['bandcamp']:
        if 'bandcamp.com' in artist_url:
            bc_url = artist_url
        else:
            bc_url = 'https://' + artist_url + '.bandcamp.com'

        filenames = scrape_bandcamp_url(bc_url, num_tracks=vargs['num_tracks'], folders=vargs['folders'])

        if vargs['open']:
            open_files(filenames)

        return

    if 'soundcloud' not in artist_url.lower():
        if vargs['group']:
            artist_url = 'https://soundcloud.com/groups/' + artist_url.lower()
        elif len(track_permalink) > 0:
            one_track = True
            track_url = 'https://soundcloud.com/' + artist_url.lower() + '/' + track_permalink.lower()
        else:
            artist_url = 'https://soundcloud.com/' + artist_url.lower()
            if vargs['likes']:
                artist_url = artist_url + '/likes'

    client = soundcloud.Client(client_id=CLIENT_ID)
    if one_track:
        resolved = client.get('/resolve', url=track_url)
    else:
        resolved = client.get('/resolve', url=artist_url)

    # This is is likely a 'likes' page.
    if not hasattr(resolved, 'kind'):
        tracks = resolved
    else:
        if resolved.kind == 'artist':
            artist = resolved
            artist_id = artist.id
            tracks = client.get('/users/' + str(artist_id) + '/tracks')
        elif resolved.kind == 'playlist':
            tracks = resolved.tracks
        elif resolved.kind == 'track':
            tracks = [resolved]
        elif resolved.kind == 'group':
            group = resolved
            group_id = group.id
            tracks = client.get('/groups/' + str(group_id) + '/tracks')
        else:
            artist = resolved
            artist_id = artist.id
            tracks = client.get('/users/' + str(artist_id) + '/tracks')

    if one_track:
        num_tracks = 1
    else:
        num_tracks = vargs['num_tracks']
    filenames = download_tracks(client, tracks, num_tracks, vargs['downloadable'], vargs['folders'])

    if vargs['open']:
        open_files(filenames)


def download_tracks(client, tracks, num_tracks=sys.maxint, downloadable=False, folders=False):

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
                        puts(colored.red(u"Skipping") + ": " + track.title.encode('utf-8'))
                        continue
                    if hasattr(track, 'stream_url'):
                        t_track['stream_url'] = track.stream_url
                    else:
                        t_track['direct'] = True
                        t_track['stream_url'] = 'https://api.soundcloud.com/tracks/' + str(track.id) + '/stream?client_id=' + MAGIC_CLIENT_ID
                track = t_track
            except Exception, e:
                puts(track.title.encode('utf-8') + colored.red(u' is not downloadable') + '.')
                continue

        if i > num_tracks - 1:
            continue
        try:
            if not track.get('stream_url', False):
                puts(track['title'].encode('utf-8') + colored.red(u' is not downloadable') + '.')
                continue
            else:
                track_artist = track['user']['username'].replace('/', '-')
                track_title = track['title'].replace('/', '-')

                track_filename = track_artist + ' - ' + track_title + '.mp3'
                if folders:
                    if not exists(track_artist):
                        mkdir(track_artist)
                    track_filename = track_artist + '/' + track_filename

                if exists(track_filename) and folders:
                    puts(colored.yellow(u"Track already downloaded: ") + track_title.encode('utf-8'))
                    continue

                puts(colored.green(u"Downloading") + ": " + track['title'].encode('utf-8'))
                if track.get('direct', False):
                    location = track['stream_url']
                else:
                    stream = client.get(track['stream_url'], allow_redirects=False)
                    if hasattr(stream, 'location'):
                        location = stream.location
                    else:
                        location = stream.url

                download_file(location, track_filename)
                tag_file(track_filename,
                        artist=track['user']['username'],
                        title=track['title'],
                        year=track['release_year'],
                        genre=track['genre'],
                        artwork_url=track['artwork_url'])
                filenames.append(track_filename)
        except Exception, e:
            puts(colored.red(u"Problem downloading ") + track['title'].encode('utf-8'))
            print 

    return filenames


def download_file(url, path):
    r = requests.get(url, stream=True)
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length / 1024) + 1):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()

    return path


def tag_file(filename, artist, title, year, genre, artwork_url, album=None, track_number=None):
    try:
        audio = EasyMP3(filename)
        audio["artist"] = artist
        audio["title"] = title
        if year:
            audio["date"] = str(year)
        if album:
            audio["album"] = album
        if track_number:
            audio["tracknumber"] = str(track_number)
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
                except Exception, e:
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
                    desc=u'Cover',
                    data=image_data
                )
            )
            audio.save()
    except Exception, e:
        print e

def open_files(filenames):
    command = ['open'] + filenames
    process = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()


# Largely borrowed from Ronier's bandcampscrape
def scrape_bandcamp_url(url, num_tracks=sys.maxint, folders=False):

    album_data = get_bandcamp_metadata(url)

    artist = album_data["artist"]
    album_name = album_data["current"]["title"]

    filenames = []

    if folders:
        directory = artist + " - " + album_name
        directory = directory.replace("/", " - ")
        if not exists(directory):
            mkdir(directory)

    for i, track in enumerate(album_data["trackinfo"]):

        if i > num_tracks - 1:
            continue

        try:
            track_name = track["title"]
            track_number = str(track["track_num"]).zfill(2)
            track_filename = '%s - %s.mp3' % (track_number, track_name)
            if folders:
                path = directory + "/" + track_filename
                if exists(path):
                    puts(colored.yellow(u"Track already downloaded: ") + track_name.encode('utf-8'))
                    continue
            else:
                path = artist + ' - ' + track_filename

            if not track['file']:
                puts(colored.yellow(u"Track unavailble for scraping: ") + track_name.encode('utf-8'))
                continue

            puts(colored.green(u"Downloading") + ': ' + track['title'].encode('utf-8'))
            download_file(track['file']['mp3-128'], path)
            year = datetime.strptime(album_data['album_release_date'], "%d %b %Y %H:%M:%S GMT").year
            tag_file(path,
                    artist,
                    track['title'],
                    album=album_data['current']['title'],
                    year=year,
                    genre='',
                    artwork_url=album_data['artFullsizeUrl'],
                    track_number=track['track_num'])

            filenames.append(path)

        except Exception, e:
            puts(colored.red(u"Problem downloading ") + track['title'].encode('utf-8'))
            print e

    return filenames


def get_bandcamp_metadata(url):
    request = requests.get(url)
    sloppy_json = request.text.split("var TralbumData = ")
    sloppy_json = sloppy_json[1].replace('" + "', "")
    sloppy_json = sloppy_json.replace("'", "\'")
    sloppy_json = sloppy_json.split("};")[0] + "};"
    sloppy_json = sloppy_json.replace("};", "}")
    return demjson.decode(sloppy_json)

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception, e:
        print e
