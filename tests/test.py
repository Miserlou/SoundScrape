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
        vargs = {'folders': False, 'group': False, 'track': '', 'num_tracks': 9223372036854775807, 'bandcamp': False, 'downloadable': False, 'likes': False, 'open': False, 'artist_url': 'https://soundcloud.com/bxsswxrshp/the-king-is-dead-and-i-couldnt-be-happier'}
        process_soundcloud(vargs)
        new_mp3_count = len(glob.glob1('', "*.mp3"))
        self.assertTrue(new_mp3_count > mp3_count)

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

        # shortest mix I could find that was still semi tolerable
        mp3_count = len(glob.glob1('', "*.mp3"))
        vargs = {'folders': False, 'group': False, 'track': '', 'num_tracks': 9223372036854775807, 'bandcamp': False, 'downloadable': False, 'likes': False, 'open': False, 'artist_url': 'https://www.mixcloud.com/Bobby_T_FS15/coffee-cigarettes-saturday-morning-hip-hop-fix/'}
        process_mixcloud(vargs)
        new_mp3_count = len(glob.glob1('', "*.mp3"))
        self.assertTrue(new_mp3_count > mp3_count)
        
        for f in glob.glob('*.mp3'):
           os.unlink(f)

if __name__ == '__main__':
    unittest.main()
