#! /usr/bin/env python

import soundcloud
import requests
import sys
import argparse

from mutagen.easyid3 import ID3, EasyID3 
from mutagen.mp3 import EasyMP3

# Please be nice with this!
CLIENT_ID = '22e566527758690e6feb2b5cb300cc43'
CLIENT_SECRET = '3a7815c3f9a82c3448ee4e7d3aa484a4'

def main():
    parser = argparse.ArgumentParser(description='SoundScrape. Scrape an artist from SoundCloud.\n')
    parser.add_argument('artist_url', metavar='U', type=str,
                   help='An artist\'s SoundCloud username or URL')
    parser.add_argument('-n', '--num-tracks', type=int, default=sys.maxint,
                        help='The number of tracks to download')

    args = parser.parse_args()
    vargs = vars(args)
    if not any(vargs.values()):
        parser.error('Please supply an artist\'s username or URL!')

    artist_url = vargs['artist_url']
    if 'soundcloud' not in artist_url.lower():
        artist_url = 'https://soundcloud.com/' + artist_url.lower()

    client = soundcloud.Client(client_id=CLIENT_ID)
    resolved = client.get('/resolve', url=artist_url)

    if resolved.kind == 'artist':
        artist = resolved
        artist_id = artist.id
        tracks = client.get('/users/' + str(artist_id) + '/tracks')
    elif resolved.kind == 'playlist':
        tracks = resolved.tracks

    num_tracks = vargs['num_tracks']
    download_tracks(client, tracks, num_tracks)

def download_tracks(client, tracks, num_tracks=sys.maxint):
    for i, track in enumerate(tracks):
        if i > num_tracks - 1:
            continue
        try:
            print u"Downloading: " + track['title']
            stream_url = client.get(track['stream_url'], allow_redirects=False)
            track_filename = track['user']['username'].replace('/', '-') + ' - ' + track['title'].replace('/', '-') + '.mp3'
            download_file(stream_url.location, track_filename)
            tag_file(track_filename, 
                    artist=track['user']['username'], 
                    title=track['title'], 
                    year=track['release_year'], 
                    genre=track['genre'])
        except Exception, e:
            print u"Problem downloading " + track['title']
            print e

def download_file(url, path):
    r = requests.get(url, stream=True)
    with open(path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): 
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
    return path

def tag_file(filename, artist, title, year, genre):
    try:
        audio = EasyMP3(filename)
        audio["artist"] = artist
        audio["title"] = title
        if year:
            audio["date"] = str(year)
        audio["genre"] = genre
        audio.save()
    except Exception, e:
        print e

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception, e:
        print e
