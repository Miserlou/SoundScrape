![SoundScrape!](http://i.imgur.com/nHAt2ow.png)

SoundScrape
==============

**SoundScrape** makes it super easy to download artists from SoundCloud - even those which don't have download links! It automatically creates ID3 tags as well, which is handy.

Usage
---------

First, install it:

```bash
pip install soundscrape
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

Folders
--------

By default, SoundScrape aims to act like _wget_, downloading in place in the current directory. With the *-f* argument, however, SoundScrape acts more like a download manager and sorts songs in to ./ARTIST_NAME/ARTIST_NAME_SONG_TITLE.mp3 format. It will also skip previously downloaded tracks.

```bash
soundscrape murdercitydevils -f
```

Issues
-------

There's probably a lot more that can be done to improve this. Please file issues if you find them!
