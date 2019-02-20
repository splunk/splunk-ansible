#!/usr/bin/env python

import os
import sys
import pytest
from mock import MagicMock

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
#FIXTURES_DIR = os.path.join(FILE_DIR, "fixtures")
REPO_DIR = os.path.join(FILE_DIR, "..", "..")

# Add environ.py into path for testing
sys.path.append(os.path.join(REPO_DIR, "inventory"))

import environ

def test_getRandomString():
	word = environ.getRandomString()
	assert len(word) == 6

@pytest.mark.parametrize(("filepath", "result"), 
	[
	    ("C:\\opt\\splunk", "/opt/splunk"),
	    ("C:\\opt\\", "/opt/"),
	    ("C:\\opt", "/opt"),
	    ("C:\\", "/"),
	    ("/opt/splunk", None)
	]
)
def test_convert_path_windows_to_nix(filepath, result):
	outcome = environ.convert_path_windows_to_nix(filepath)
	assert outcome == result
