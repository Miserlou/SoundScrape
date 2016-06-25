import glob
import os
import re
import string
import sys
import unittest

import nose
from nose import case
from nose.pyversion import unbound_method
from nose import util

from soundscrape.soundscrape import get_client
from soundscrape.soundscrape import process_soundcloud
from soundscrape.soundscrape import process_bandcamp
from soundscrape.soundscrape import process_mixcloud
from soundscrape.soundscrape import process_audiomack

class TestSoundscrape(unittest.TestCase):

    ##
    # Basic Tests
    ##

    def test_test(self):
        self.assertTrue(True)

    def test_get_client(self):
        client = get_client()
        self.assertTrue(bool(client))

    def test_soundcloud(self):
        for f in glob.glob('*.mp3'):
           os.unlink(f)

        mp3_count = len(glob.glob1('', "*.mp3"))
        vargs = {'folders': False, 'group': False, 'track': '', 'num_tracks': 9223372036854775807, 'bandcamp': False, 'downloadable': False, 'likes': False, 'open': False, 'artist_url': 'https://soundcloud.com/fzpz/revised', 'keep': True}
        process_soundcloud(vargs)
        new_mp3_count = len(glob.glob1('', "*.mp3"))
        self.assertTrue(new_mp3_count > mp3_count)

        for f in glob.glob('*.mp3'):
           os.unlink(f)

    def test_soundcloud_hard(self):
        for f in glob.glob('*.mp3'):
           os.unlink(f)

        mp3_count = len(glob.glob1('', "*.mp3"))
        vargs = {'folders': False, 'group': False, 'track': '', 'num_tracks': 3, 'bandcamp': False, 'downloadable': False, 'likes': False, 'open': False, 'artist_url': 'puptheband', 'keep': False}
        process_soundcloud(vargs)
        new_mp3_count = len(glob.glob1('', "*.mp3"))
        self.assertTrue(new_mp3_count > mp3_count)
        self.assertTrue(new_mp3_count == 3)

        for f in glob.glob('*.mp3'):
           os.unlink(f)

    def test_bandcamp(self):
        for f in glob.glob('*.mp3'):
           os.unlink(f)

        mp3_count = len(glob.glob1('', "*.mp3"))
        vargs = {'folders': False, 'group': False, 'track': '', 'num_tracks': 9223372036854775807, 'bandcamp': False, 'downloadable': False, 'likes': False, 'open': False, 'artist_url': 'https://atenrays.bandcamp.com/track/who-u-think'}
        process_bandcamp(vargs)
        new_mp3_count = len(glob.glob1('', "*.mp3"))
        self.assertTrue(new_mp3_count > mp3_count)
        
        for f in glob.glob('*.mp3'):
           os.unlink(f)

    def test_bandcamp_slashes(self):
        for f in glob.glob('*.mp3'):
           os.unlink(f)

        mp3_count = len(glob.glob1('', "*.mp3"))
        vargs = {'folders': False, 'group': False, 'track': '', 'num_tracks': 9223372036854775807, 'bandcamp': False, 'downloadable': False, 'likes': False, 'open': False, 'artist_url': 'https://defill.bandcamp.com/track/amnesia-chamber-harvest-skit'}
        process_bandcamp(vargs)
        new_mp3_count = len(glob.glob1('', "*.mp3"))
        self.assertTrue(new_mp3_count > mp3_count)
        
        for f in glob.glob('*.mp3'):
           os.unlink(f)

    def test_mixcloud(self):

        for f in glob.glob('*.mp3'):
           os.unlink(f)

        for f in glob.glob('*.m4a'):
           os.unlink(f)

        # shortest mix I could find that was still semi tolerable
        mp3_count = len(glob.glob1('', "*.mp3"))
        m4a_count = len(glob.glob1('', "*.m4a"))
        vargs = {'folders': False, 'group': False, 'track': '', 'num_tracks': 9223372036854775807, 'bandcamp': False, 'downloadable': False, 'likes': False, 'open': False, 'artist_url': 'https://www.mixcloud.com/Bobby_T_FS15/coffee-cigarettes-saturday-morning-hip-hop-fix/'}
        process_mixcloud(vargs)
        new_mp3_count = len(glob.glob1('', "*.mp3"))
        new_m4a_count = len(glob.glob1('', "*.m4a"))
        self.assertTrue((new_mp3_count > mp3_count) or (new_m4a_count > m4a_count))
        
        for f in glob.glob('*.mp3'):
           os.unlink(f)

        for f in glob.glob('*.m4a'):
           os.unlink(f)

    def test_audiomack(self):
        for f in glob.glob('*.mp3'):
           os.unlink(f)

        mp3_count = len(glob.glob1('', "*.mp3"))
        vargs = {'folders': False, 'group': False, 'track': '', 'num_tracks': 9223372036854775807, 'bandcamp': False, 'audiomack': True, 'downloadable': False, 'likes': False, 'open': False, 'artist_url': 'https://www.audiomack.com/song/bottomfeedermusic/power'}
        process_audiomack(vargs)
        new_mp3_count = len(glob.glob1('', "*.mp3"))
        self.assertTrue(new_mp3_count > mp3_count)
        
        for f in glob.glob('*.mp3'):
           os.unlink(f)

if __name__ == '__main__':
    unittest.main()
