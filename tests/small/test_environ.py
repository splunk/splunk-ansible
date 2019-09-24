#!/usr/bin/env python
'''
Unit tests for inventory/environ.py
'''
from __future__ import absolute_import

import os
import sys
import pytest
from mock import MagicMock, patch

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
    with patch("os.environ", new={"FOOBAR": "123", "BARFOO": "456"}):
        r = environ.getVars(regex)
        assert r == result

@patch('environ.loadDefaultSplunkVariables', return_value={"splunk": {"build_location": None}})
@patch('environ.overrideEnvironmentVars')
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

@pytest.mark.parametrize(("vars_scope", "trigger_splunkbase", "os_env", "apps_count"),
                         [
                            # Check variety of splunkbase parameters
                            ({}, False, {}, 0),
                            ({"splunkbase_username": "ocho"}, False, {}, 0),
                            ({"splunkbase_password": "cinco"}, False, {}, 0),
                            ({"splunkbase_username": "ocho", "splunkbase_password": "cinco"}, True, {}, 0),
                            # Check variety of environment variable parameters
                            ({}, False, {"SPLUNK_APPS": "hi"}, 0),
                            ({}, False, {"SPLUNK_APPS_URL": "hi"}, 1),
                            ({}, False, {"SPLUNK_APPS_URL": "a,b,ccccc,dd"}, 4),
                            # Sanity check the combination of splunkbase params + env vars work
                            ({"splunkbase_username": "ocho"}, False, {"SPLUNKBASE_USERNAME": "qwerty"}, 0),
                            ({"splunkbase_password": "cinco"}, False, {"SPLUNKBASE_PASSWORD": "qwerty"}, 0),
                            ({"splunkbase_username": "ocho"}, True, {"SPLUNKBASE_PASSWORD": "cinco"}, 0),
                            ({"splunkbase_password": "cinco"}, True, {"SPLUNKBASE_USERNAME": "ocho"}, 0),
                            ({}, True, {"SPLUNKBASE_USERNAME": "ocho", "SPLUNKBASE_PASSWORD": "cinco"}, 0),
                            ({"splunkbase_username": "ocho"}, False, {"SPLUNKBASE_USERNAME": "qwerty", "SPLUNK_APPS_URL": "a,b,dd"}, 3),
                            ({"splunkbase_password": "cinco"}, False, {"SPLUNKBASE_PASSWORD": "qwerty", "SPLUNK_APPS_URL": "a,b,dd"}, 3),
                            ({"splunkbase_username": "ocho"}, True, {"SPLUNKBASE_PASSWORD": "cinco", "SPLUNK_APPS_URL": "a,b,dd"}, 3),
                            ({"splunkbase_password": "cinco"}, True, {"SPLUNKBASE_USERNAME": "ocho", "SPLUNK_APPS_URL": "a,b,dd"}, 3),
                            ({}, True, {"SPLUNKBASE_USERNAME": "ocho", "SPLUNKBASE_PASSWORD": "cinco", "SPLUNK_APPS_URL": "a,b,dd"}, 3),
                         ]
                        )
def test_getSplunkApps(vars_scope, trigger_splunkbase, os_env, apps_count):
    vars_scope["splunk"] = {}
    with patch("environ.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, content="<id>123abc</id>")
        with patch("os.environ", new=os_env):
            environ.getSplunkApps(vars_scope)
        # Make sure Splunkbase token is populated when appropriate
        if trigger_splunkbase:
            mock_post.assert_called_with("https://splunkbase.splunk.com/api/account:login/", data={"username": "ocho", "password": "cinco"})
            assert vars_scope.get("splunkbase_token") == "123abc"
        else:
            mock_post.assert_not_called()
            assert not vars_scope.get("splunkbase_token")
    # Check that the SPLUNK_APPS_URL gets assigned
    assert len(vars_scope["splunk"].get("apps_location")) == apps_count

def test_getSplunkApps_exception():
    with patch("environ.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=400, content="error")
        try:
            environ.getSplunkApps({"splunkbase_username": "ocho", "splunkbase_password": "cinco"})
            assert False
        except Exception as e:
            assert True
            assert "Invalid Splunkbase credentials" in str(e)
