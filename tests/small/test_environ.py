#!/usr/bin/env python
'''
Unit tests for inventory/environ.py
'''
from __future__ import absolute_import

import os
import sys
import pytest
import mock

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
#FIXTURES_DIR = os.path.join(FILE_DIR, "fixtures")
REPO_DIR = os.path.join(FILE_DIR, "..", "..")

# Add environ.py into path for testing
sys.path.append(os.path.join(REPO_DIR, "inventory"))

import environ

@pytest.mark.parametrize(("regex", "result"),
                         [
                             (r"(FOOBAR)", {"foobar": "123"}),
                             (r"^FOO(.*)", {"bar": "123"}),
                         ]
                        )
def test_getVars(regex, result):
    '''
    This method makes the assumption that there will always be a group(1),
    So if doing an exact string match, for now group the entire string
    '''
    with mock.patch("os.environ", new={"FOOBAR": "123", "BARFOO": "456"}):
        r = environ.getVars(regex)
        assert r == result

@mock.patch('environ.loadDefaultSplunkVariables', return_value={"splunk": {"build_location": None}})
@mock.patch('environ.overrideEnvironmentVars')
def test_getDefaultVars(mock_overrideEnvironmentVars, mock_loadDefaultSplunkVariables):
    '''
    Unit test for getting our default variables
    '''
    retval = environ.getDefaultVars()
    assert "splunk" in retval

def test_getRandomString():
    '''
    Test coverage for getting random string
    '''
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
    '''
    Unit tests
    '''
    outcome = environ.convert_path_windows_to_nix(filepath)
    assert outcome == result
