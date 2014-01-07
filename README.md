![SoundScrape!](http://i.imgur.com/nHAt2ow.png)

SoundScrape
==============

**SoundScrape** makes it super easy to download artists from SoundCloud. It even automatically creates ID3 tags as well, which is handy.

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

Issues
-------

There's probably a lot more that can be done to improve this. Please file issues if you find them!
