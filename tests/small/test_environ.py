#!/usr/bin/env python
'''
Unit tests for inventory/environ.py
'''
from __future__ import absolute_import

import os
import sys
import pytest
import requests
from mock import MagicMock, patch, mock_open

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

@pytest.mark.skip(reason="TODO")
def test_getSplunkInventory():
    pass

@patch('environ.loadDefaults', return_value={"splunk": {"http_port": 8000, "build_location": None}})
@patch('environ.overrideEnvironmentVars')
@patch('environ.getSecrets')
@patch('environ.getHEC')
def test_getDefaultVars(mock_overrideEnvironmentVars, mock_loadDefaultSplunkVariables, mock_getSecrets, mock_getHEC):
    '''
    Unit test for getting our default variables
    '''
    retval = environ.getDefaultVars()
    assert "splunk" in retval

@pytest.mark.parametrize(("default_yml", "os_env", "output"),
            [
                # Check null parameters
                ({}, {}, {"opt": None, "home": None, "exec": None, "pid": None}),
                # Check default.yml parameters
                ({"opt": "/opt"}, {}, {"opt": "/opt", "home": None, "exec": None, "pid": None}),
                ({"home": "/tmp/splunk"}, {}, {"opt": None, "home": "/tmp/splunk", "exec": None, "pid": None}),
                ({"exec": "/opt/splunk/bin/splunk"}, {}, {"opt": None, "home": None, "exec": "/opt/splunk/bin/splunk", "pid": None}),
                ({"pid": "/splunk.pid"}, {}, {"opt": None, "home": None, "exec": None, "pid": "/splunk.pid"}),
                # Check environment variable parameters
                ({}, {"SPLUNK_OPT": "/home/"}, {"opt": "/home/", "home": None, "exec": None, "pid": None}),
                ({}, {"SPLUNK_HOME": "/home/"}, {"opt": None, "home": "/home/", "exec": None, "pid": None}),
                ({}, {"SPLUNK_EXEC": "/home/splunk.exe"}, {"opt": None, "home": None, "exec": "/home/splunk.exe", "pid": None}),
                ({}, {"SPLUNK_PID": "/home/splunk.pid"}, {"opt": None, "home": None, "exec": None, "pid": "/home/splunk.pid"}),
                # Check the union combination of default.yml + environment variables and order of precedence when overwriting
                ({"opt": "/home"}, {"SPLUNK_OPT": "/opt"}, {"opt": "/opt", "home": None, "exec": None, "pid": None}),
                ({"home": "/tmp/splunk"}, {"SPLUNK_HOME": "/opt/splunk"}, {"opt": None, "home": "/opt/splunk", "exec": None, "pid": None}),
                ({"exec": "/bin/splunk"}, {"SPLUNK_EXEC": "/opt/splunk/bin/splunk"}, {"opt": None, "home": None, "exec": "/opt/splunk/bin/splunk", "pid": None}),
                ({"pid": "/splunk.pid"}, {"SPLUNK_PID": "/opt/splunk/splunk.pid"}, {"opt": None, "home": None, "exec": None, "pid": "/opt/splunk/splunk.pid"}),
            ]
        )
def test_getSplunkPaths(default_yml, os_env, output):
    vars_scope = {"splunk": default_yml}
    with patch("os.environ", new=os_env):
        environ.getSplunkPaths(vars_scope)
    assert type(vars_scope["splunk"]) == dict
    assert vars_scope["splunk"] == output

@pytest.mark.parametrize(("default_yml", "os_env", "output"),
            [
                # Check null parameters
                ({}, {}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1, "search_factor": 1}),
                # Check default.yml parameters
                ({"idxc": {}}, {}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"label": None}}, {}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"label": "1234"}}, {}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": "1234", "secret": None, "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"secret": None}}, {}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"secret": "1234"}}, {}, {"pass4SymmKey": "1234", "discoveryPass4SymmKey": "1234", "label": None, "secret": "1234", "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"pass4SymmKey": None}}, {}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"pass4SymmKey": "1234"}}, {}, {"pass4SymmKey": "1234", "discoveryPass4SymmKey": "1234", "label": None, "secret": "1234", "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"discoveryPass4SymmKey": None}}, {}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"discoveryPass4SymmKey": "1234"}}, {}, {"pass4SymmKey": None, "discoveryPass4SymmKey": "1234", "label": None, "secret": None, "replication_factor": 1, "search_factor": 1}),
                # Search factor should never exceed replication factor
                ({"idxc": {"replication_factor": 0, "search_factor": 2}}, {}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 0, "search_factor": 0}),
                ({"idxc": {"replication_factor": 1, "search_factor": 3}}, {}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"replication_factor": "2", "search_factor": 3}}, {}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 2, "search_factor": 2}),
                # This should return replication_factor=2 because there are only 2 hosts in the "splunk_indexer" group
                ({"idxc": {"replication_factor": 3, "search_factor": 1}}, {}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 2, "search_factor": 1}),
                # Check environment variable parameters
                ({}, {"SPLUNK_IDXC_LABEL": ""}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": "", "secret": None, "replication_factor": 1, "search_factor": 1}),
                ({}, {"SPLUNK_IDXC_LABEL": "abcd"}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": "abcd", "secret": None, "replication_factor": 1, "search_factor": 1}),
                ({}, {"SPLUNK_IDXC_SECRET": ""}, {"pass4SymmKey": "", "discoveryPass4SymmKey": "", "label": None, "secret": "", "replication_factor": 1, "search_factor": 1}),
                ({}, {"SPLUNK_IDXC_SECRET": "abcd"}, {"pass4SymmKey": "abcd", "discoveryPass4SymmKey": "abcd", "label": None, "secret": "abcd", "replication_factor": 1, "search_factor": 1}),
                ({}, {"SPLUNK_IDXC_PASS4SYMMKEY": "abcd"}, {"pass4SymmKey": "abcd", "discoveryPass4SymmKey": "abcd", "label": None, "secret": "abcd", "replication_factor": 1, "search_factor": 1}),
                ({}, {"SPLUNK_IDXC_REPLICATION_FACTOR": "1"}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1, "search_factor": 1}),
                ({}, {"SPLUNK_IDXC_REPLICATION_FACTOR": 2, "SPLUNK_IDXC_SEARCH_FACTOR": "1"}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 2, "search_factor": 1}),
                ({}, {"SPLUNK_IDXC_DISCOVERYPASS4SYMMKEY": "qwerty"}, {"pass4SymmKey": None, "discoveryPass4SymmKey": "qwerty", "label": None, "secret": None, "replication_factor": 1, "search_factor": 1}),
                # Check the union combination of default.yml + environment variables and order of precedence when overwriting
                ({"idxc": {"label": "1234"}}, {"SPLUNK_IDXC_LABEL": "abcd"}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": "abcd", "secret": None, "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"secret": "abcd"}}, {"SPLUNK_IDXC_SECRET": "1234"}, {"pass4SymmKey": "1234", "discoveryPass4SymmKey": "1234", "label": None, "secret": "1234", "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"pass4SymmKey": "1234"}}, {"SPLUNK_IDXC_PASS4SYMMKEY": "abcd"}, {"pass4SymmKey": "abcd", "discoveryPass4SymmKey": "abcd", "label": None, "secret": "abcd", "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"pass4SymmKey": "1234", "discoveryPass4SymmKey": "7890"}}, {"SPLUNK_IDXC_PASS4SYMMKEY": "abcd"}, {"pass4SymmKey": "abcd", "discoveryPass4SymmKey": "7890", "label": None, "secret": "abcd", "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"pass4SymmKey": "1234", "discoveryPass4SymmKey": "7890"}}, {"SPLUNK_IDXC_DISCOVERYPASS4SYMMKEY": "zxcv", "SPLUNK_IDXC_PASS4SYMMKEY": "abcd"}, {"pass4SymmKey": "abcd", "discoveryPass4SymmKey": "zxcv", "label": None, "secret": "abcd", "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"secret": "abcd"}}, {"SPLUNK_IDXC_SECRET": "1234"}, {"pass4SymmKey": "1234", "discoveryPass4SymmKey": "1234", "label": None, "secret": "1234", "replication_factor": 1, "search_factor": 1}),
                ({"idxc": {"replication_factor": 3, "search_factor": 3}}, {"SPLUNK_IDXC_REPLICATION_FACTOR": 2}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 2, "search_factor": 2}),
                ({"idxc": {"replication_factor": 2, "search_factor": 2}}, {"SPLUNK_IDXC_SEARCH_FACTOR": 1}, {"pass4SymmKey": None, "discoveryPass4SymmKey": None, "label": None, "secret": None, "replication_factor": 2, "search_factor": 1}),
            ]
        )
def test_getIndexerClustering(default_yml, os_env, output):
    vars_scope = {"splunk": default_yml}
    with patch("environ.inventory", {"splunk_indexer": {"hosts": ["a", "b"]}}) as mock_inven:
        with patch("os.environ", new=os_env):
            environ.getIndexerClustering(vars_scope)
    assert type(vars_scope["splunk"]["idxc"]) == dict
    assert vars_scope["splunk"]["idxc"] == output

@pytest.mark.parametrize(("default_yml", "os_env", "output"),
            [
                # Check null parameters
                ({}, {}, {"pass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1}),
                # Check default.yml parameters
                ({"shc": {}}, {}, {"pass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1}),
                ({"shc": {"label": None}}, {}, {"pass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1}),
                ({"shc": {"label": "1234"}}, {}, {"pass4SymmKey": None, "label": "1234", "secret": None, "replication_factor": 1}),
                ({"shc": {"secret": None}}, {}, {"pass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1}),
                ({"shc": {"secret": "1234"}}, {}, {"pass4SymmKey": "1234", "label": None, "secret": "1234", "replication_factor": 1}),
                ({"shc": {"pass4SymmKey": None}}, {}, {"pass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1}),
                ({"shc": {"pass4SymmKey": "1234"}}, {}, {"pass4SymmKey": "1234", "label": None, "secret": "1234", "replication_factor": 1}),
                ({"shc": {"replication_factor": 0}}, {}, {"pass4SymmKey": None, "label": None, "secret": None, "replication_factor": 0}),
                ({"shc": {"replication_factor": 1}}, {}, {"pass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1}),
                ({"shc": {"replication_factor": "2"}}, {}, {"pass4SymmKey": None, "label": None, "secret": None, "replication_factor": 2}),
                # This should return replication_factor=2 because there are only 2 hosts in the "splunk_search_head" group
                ({"shc": {"replication_factor": 3}}, {}, {"pass4SymmKey": None, "label": None, "secret": None, "replication_factor": 2}),
                # Check environment variable parameters
                ({}, {"SPLUNK_SHC_LABEL": ""}, {"pass4SymmKey": None, "label": "", "secret": None, "replication_factor": 1}),
                ({}, {"SPLUNK_SHC_LABEL": "abcd"}, {"pass4SymmKey": None,"label": "abcd", "secret": None, "replication_factor": 1}),
                ({}, {"SPLUNK_SHC_SECRET": ""}, {"pass4SymmKey": "", "label": None, "secret": "", "replication_factor": 1}),
                ({}, {"SPLUNK_SHC_SECRET": "abcd"}, {"pass4SymmKey": "abcd", "label": None, "secret": "abcd", "replication_factor": 1}),
                ({}, {"SPLUNK_SHC_PASS4SYMMKEY": "abcd"}, {"pass4SymmKey": "abcd", "label": None, "secret": "abcd", "replication_factor": 1}),
                ({}, {"SPLUNK_SHC_REPLICATION_FACTOR": "2"}, {"pass4SymmKey": None, "label": None, "secret": None, "replication_factor": 2}),
                # Check the union combination of default.yml + environment variables and order of precedence when overwriting
                ({"shc": {"label": "1234"}}, {"SPLUNK_SHC_LABEL": "abcd"}, {"pass4SymmKey": None, "label": "abcd", "secret": None, "replication_factor": 1}),
                ({"shc": {"secret": "abcd"}}, {"SPLUNK_SHC_SECRET": "1234"}, {"pass4SymmKey": "1234", "label": None, "secret": "1234", "replication_factor": 1}),
                ({"shc": {"pass4SymmKey": "1234"}}, {"SPLUNK_SHC_PASS4SYMMKEY": "abcd"}, {"pass4SymmKey": "abcd", "label": None, "secret": "abcd", "replication_factor": 1}),
                ({"shc": {"replication_factor": 2}}, {"SPLUNK_SHC_REPLICATION_FACTOR": "1"}, {"pass4SymmKey": None, "label": None, "secret": None, "replication_factor": 1}),
            ]
        )
def test_getSearchHeadClustering(default_yml, os_env, output):
    vars_scope = {"splunk": default_yml}
    with patch("environ.inventory", {"splunk_search_head": {"hosts": ["a", "b"]}}) as mock_inven:
        with patch("os.environ", new=os_env):
            environ.getSearchHeadClustering(vars_scope)
    assert type(vars_scope["splunk"]["shc"]) == dict
    assert vars_scope["splunk"]["shc"] == output

@pytest.mark.skip(reason="TODO")
def test_getMultisite():
    pass

@pytest.mark.skip(reason="TODO")
def test_getSplunkWebSSL():
    pass

@pytest.mark.parametrize(("default_yml", "os_env", "output"),
    [
        # Check null parameters
        ({}, {}, {"ca": None, "cert": None, "password": None, "enable": True}),
        ({"does-not-exist": True}, {}, {"ca": None, "cert": None, "password": None, "enable": True}),
        # Check default.yml parameters
        ({"ssl": {"enable": False}}, {}, {"ca": None, "cert": None, "password": None, "enable": False}),
        ({"ssl": {"ca": "hi"}}, {}, {"ca": "hi", "cert": None, "password": None, "enable": True}),
        ({"ssl": {"cert": "hi"}}, {}, {"ca": None, "cert": "hi", "password": None, "enable": True}),
        ({"ssl": {"password": "hi"}}, {}, {"ca": None, "cert": None, "password": "hi", "enable": True}),
        ({"ssl": {"ca": "aaa", "cert": "bbb", "password": "ccc", "enable": False}}, {}, {"ca": "aaa", "cert": "bbb", "password": "ccc", "enable": False}),
        # Check environment variable parameters
        ({}, {"SPLUNKD_SSL_CA": "hi"}, {"ca": "hi", "cert": None, "password": None, "enable": True}),
        ({}, {"SPLUNKD_SSL_CERT": "hi"}, {"ca": None, "cert": "hi", "password": None, "enable": True}),
        ({}, {"SPLUNKD_SSL_PASSWORD": "hi"}, {"ca": None, "cert": None, "password": "hi", "enable": True}),
        ({}, {"SPLUNKD_SSL_ENABLE": "true"}, {"ca": None, "cert": None, "password": None, "enable": True}),
        ({}, {"SPLUNKD_SSL_ENABLE": "false"}, {"ca": None, "cert": None, "password": None, "enable": False}),
        ({}, {"SPLUNKD_SSL_ENABLE": "False"}, {"ca": None, "cert": None, "password": None, "enable": False}),
        # Check the union combination of default.yml + environment variables and order of precedence when overwriting
        ({"ssl": {"ca": "value1"}}, {"SPLUNKD_SSL_CA": "value2"}, {"ca": "value2", "cert": None, "password": None, "enable": True}),
        ({"ssl": {"cert": "value1"}}, {"SPLUNKD_SSL_CERT": "value2"}, {"ca": None, "cert": "value2", "password": None, "enable": True}),
        ({"ssl": {"password": "value1"}}, {"SPLUNKD_SSL_PASSWORD": "value2"}, {"ca": None, "cert": None, "password": "value2", "enable": True}),
        ({}, {"SPLUNKD_SSL_ENABLE": "true"}, {"ca": None, "cert": None, "password": None, "enable": True}),
        ({}, {"SPLUNKD_SSL_ENABLE": "false"}, {"ca": None, "cert": None, "password": None, "enable": False}),
        ({"ssl": {"enable": True}}, {"SPLUNKD_SSL_ENABLE": "FALSE"}, {"ca": None, "cert": None, "password": None, "enable": False}),
        ({"ssl": {"enable": True}}, {"SPLUNKD_SSL_ENABLE": "FaLsE"}, {"ca": None, "cert": None, "password": None, "enable": False}),
        ({"ssl": {"enable": False}}, {"SPLUNKD_SSL_ENABLE": ""}, {"ca": None, "cert": None, "password": None, "enable": False}),
    ]
)
def test_getSplunkdSSL(default_yml, os_env, output):
    vars_scope = {"splunk": default_yml}
    with patch("os.environ", new=os_env):
        environ.getSplunkdSSL(vars_scope)
    assert type(vars_scope["splunk"]) == dict
    assert type(vars_scope["splunk"]["ssl"]) == dict
    assert vars_scope["splunk"]["ssl"] == output

@pytest.mark.parametrize(("default_yml", "os_env", "output"),
            [
                # Check null parameters - Splunk password is required
                ({"password": "helloworld"}, {}, {"password": "helloworld", "declarative_admin_password": False, "pass4SymmKey": None, "secret": None}),
                # Check default.yml parameters
                ({"password": "helloworld", "pass4SymmKey": "you-will-never-guess", "secret": None}, {}, {"password": "helloworld", "declarative_admin_password": False, "pass4SymmKey": "you-will-never-guess", "secret": None}),
                ({"password": "helloworld", "pass4SymmKey": "you-will-never-guess", "secret": "1234"}, {}, {"password": "helloworld", "declarative_admin_password": False, "pass4SymmKey": "you-will-never-guess", "secret": "1234"}),
                ({"password": "helloworld", "secret": "1234"}, {}, {"password": "helloworld", "declarative_admin_password": False, "pass4SymmKey": None, "secret": "1234"}),
                ({"password": "helloworld", "declarative_admin_password": True, "pass4SymmKey": "you-will-never-guess", "secret": None}, {}, {"password": "helloworld", "declarative_admin_password": True, "pass4SymmKey": "you-will-never-guess", "secret": None}),
                ({"password": "helloworld", "declarative_admin_password": True, "pass4SymmKey": "you-will-never-guess", "secret": "1234"}, {}, {"password": "helloworld", "declarative_admin_password": True, "pass4SymmKey": "you-will-never-guess", "secret": "1234"}),
                ({"password": "helloworld", "declarative_admin_password": True, "secret": "1234"}, {}, {"password": "helloworld", "declarative_admin_password": True, "pass4SymmKey": None, "secret": "1234"}),
                # Check environment variable parameters
                ({"password": None}, {"SPLUNK_PASSWORD": "helloworld", "SPLUNK_PASS4SYMMKEY": "you-will-never-guess"}, {"password": "helloworld", "declarative_admin_password": False, "pass4SymmKey": "you-will-never-guess", "secret": None}),
                ({"password": None}, {"SPLUNK_PASSWORD": "helloworld", "SPLUNK_PASS4SYMMKEY": "you-will-never-guess", "SPLUNK_SECRET": "1234"}, {"password": "helloworld", "declarative_admin_password": False, "pass4SymmKey": "you-will-never-guess", "secret": "1234"}),
                ({"password": None}, {"SPLUNK_PASSWORD": "helloworld", "SPLUNK_SECRET": "1234"}, {"password": "helloworld", "declarative_admin_password": False, "pass4SymmKey": None, "secret": "1234"}),
                ({"password": None}, {"SPLUNK_PASSWORD": "helloworld", "SPLUNK_DECLARATIVE_ADMIN_PASSWORD": "true", "SPLUNK_PASS4SYMMKEY": "you-will-never-guess"}, {"password": "helloworld", "declarative_admin_password": True, "pass4SymmKey": "you-will-never-guess", "secret": None}),
                ({"password": None}, {"SPLUNK_PASSWORD": "helloworld", "SPLUNK_DECLARATIVE_ADMIN_PASSWORD": "TRUE", "SPLUNK_PASS4SYMMKEY": "you-will-never-guess", "SPLUNK_SECRET": "1234"}, {"password": "helloworld", "declarative_admin_password": True, "pass4SymmKey": "you-will-never-guess", "secret": "1234"}),
                # We currently don't support 'yes' as a valid boolean
                ({"password": None}, {"SPLUNK_PASSWORD": "helloworld", "SPLUNK_DECLARATIVE_ADMIN_PASSWORD": "yes", "SPLUNK_SECRET": "1234"}, {"password": "helloworld", "declarative_admin_password": False, "pass4SymmKey": None, "secret": "1234"})
            ]
        )
def test_getSecrets(default_yml, os_env, output):
    vars_scope = {"splunk": default_yml}
    with patch("environ.inventory") as mock_inven:
        with patch("os.environ", new=os_env):
            with patch("environ.os.path") as mock_os_path:
                mock_os_path.isfile = MagicMock()
                mock_os_path.isfile.return_value = False
                environ.getSecrets(vars_scope)
    assert vars_scope["splunk"] == output

@pytest.mark.parametrize(("default_yml", "os_env", "output"),
            [
                # Check when Splunk password is a file
                ({"password": "/tmp/splunk-password"}, {}, {"password": "worldneversayshiback", "pass4SymmKey": None, "secret": None}),
                ({"password": "helloworld"}, {"SPLUNK_PASSWORD": "/tmp/splunk-password"}, {"password": "worldneversayshiback", "pass4SymmKey": None, "secret": None}),
            ]
        )
def test_getSecrets_passwordFromFile(default_yml, os_env, output):
    file_contents = """

worldneversayshiback

"""
    m = mock_open(read_data=file_contents)
    vars_scope = {"splunk": default_yml}
    with patch("environ.open", m, create=True) as mopen:
        with patch("environ.inventory") as mock_inven:
            with patch("os.environ", new=os_env):
                with patch("os.path") as mock_os_path:
                    # Make sure that the isfile() check returns True
                    mock_os_path.isfile = MagicMock()
                    mock_os_path.isfile.return_value = True
                    environ.getSecrets(vars_scope)
                    mopen.assert_called_once()
    assert vars_scope["splunk"]["password"] == "worldneversayshiback"


@pytest.mark.parametrize(("default_yml"),
            [
                # Check null parameters
                ({}),
                ({"password": None}),
                ({"password": ""})
            ]
        )
def test_noSplunkPassword(default_yml):
    vars_scope = {"splunk": default_yml}
    with pytest.raises(Exception) as exc:
        with patch("environ.inventory") as mock_inven:
            with patch("os.environ", new={}):
                environ.getSecrets(vars_scope)
    assert "Splunk password must be supplied!" in str(exc.value)

@pytest.mark.parametrize(("default_yml", "os_env", "output"),
            [
                # Check null parameters
                ({}, {}, {"launch": {}}),
                # Check default.yml parameters
                ({"launch": {}}, {}, {"launch": {}}),
                ({"launch": {"A": "B"}}, {}, {"launch": {"A": "B"}}),
                ({"launch": {"A": "B", "C": "D"}}, {}, {"launch": {"A": "B", "C": "D"}}),
                # Check environment variable parameters
                ({}, {"SPLUNK_LAUNCH_CONF": None}, {"launch": {}}),
                ({}, {"SPLUNK_LAUNCH_CONF": ""}, {"launch": {}}),
                ({}, {"SPLUNK_LAUNCH_CONF": "AAA=BBB"}, {"launch": {"AAA": "BBB"}}),
                ({}, {"SPLUNK_LAUNCH_CONF": "AAA=BBB,CCC=DDD"}, {"launch": {"AAA": "BBB", "CCC": "DDD"}}),
                ({}, {"SPLUNK_LAUNCH_CONF": "AAA=BBB=CCC,DDD=EEE=FFF"}, {"launch": {"AAA": "BBB=CCC", "DDD": "EEE=FFF"}}),
                # Check both
                ({"launch": {"A": "B", "C": "D"}}, {"SPLUNK_LAUNCH_CONF": "A=E,C=D"}, {"launch": {"A": "E", "C": "D"}}),
            ]
        )
def test_getLaunchConf(default_yml, os_env, output):
    vars_scope = {"splunk": default_yml}
    with patch("environ.inventory") as mock_inven:
        with patch("os.environ", new=os_env):
            environ.getLaunchConf(vars_scope)
    assert vars_scope["splunk"] == output

@pytest.mark.parametrize(("value", "separator", "output"),
            [
                # Check null value
                (None, ",", []),
                # Check empty value
                ("", ",", []),
                # Check string value
                ("a", ",", ["a"]),
                # Check comma separated string value
                ("a,b,c", ",", ["a", "b", "c"]),
                # Check list value
                (["a"], ",", ["a"]),
                (["a", "b", "c"], ",", ["a", "b", "c"])
            ]
        )
def test_ensureListValue(value, separator, output):
    result = environ.ensureListValue(value, separator)
    assert result == output

@pytest.mark.parametrize(("value", "separator", "output"),
            [
                # Check null value
                (None, ",", []),
                # Check empty value
                ("", ",", []),
                # Check string value
                ("a", ",", ["a"]),
                # Check comma separated string value
                ("a,b,c", ",", ["a", "b", "c"]),
                # Check comma separated string value with whitespaces
                (" a, b,c ", ",", ["a", "b", "c"]),
            ]
        )
def test_splitAndStrip(value, separator, output):
    result = environ.splitAndStrip(value, separator)
    assert result == output

@pytest.mark.parametrize(("default_yml", "os_env", "output"),
            [
                # Check null parameters
                ({}, {}, {"ansible_pre_tasks": [], "ansible_post_tasks": [], "ansible_environment": {}}),
                # Check ansible_pre_tasks using defaults or env vars
                ({"ansible_pre_tasks": ""}, {}, {"ansible_pre_tasks": [], "ansible_post_tasks": [], "ansible_environment": {}}),
                ({"ansible_pre_tasks": None}, {}, {"ansible_pre_tasks": [], "ansible_post_tasks": [], "ansible_environment": {}}),
                ({"ansible_pre_tasks": "a"}, {}, {"ansible_pre_tasks": ["a"], "ansible_post_tasks": [], "ansible_environment": {}}),
                ({"ansible_pre_tasks": ["a"]}, {}, {"ansible_pre_tasks": ["a"], "ansible_post_tasks": [], "ansible_environment": {}}),
                ({"ansible_pre_tasks": "a,b,c"}, {}, {"ansible_pre_tasks": ["a","b","c"], "ansible_post_tasks": [], "ansible_environment": {}}),
                ({"ansible_pre_tasks": ["a","b","c"]}, {}, {"ansible_pre_tasks": ["a","b","c"], "ansible_post_tasks": [], "ansible_environment": {}}),
                ({}, {"SPLUNK_ANSIBLE_PRE_TASKS": "d"}, {"ansible_pre_tasks": ["d"], "ansible_post_tasks": [], "ansible_environment": {}}),
                ({}, {"SPLUNK_ANSIBLE_PRE_TASKS": "e,f,g"}, {"ansible_pre_tasks": ["e","f","g"], "ansible_post_tasks": [], "ansible_environment": {}}),
                ({"ansible_pre_tasks": "a,b,c"}, {"SPLUNK_ANSIBLE_PRE_TASKS": "e,f,g"}, {"ansible_pre_tasks": ["e","f","g"], "ansible_post_tasks": [], "ansible_environment": {}}),
                ({"ansible_pre_tasks": ["a","b","c"]}, {"SPLUNK_ANSIBLE_PRE_TASKS": "e,f,g"}, {"ansible_pre_tasks": ["e","f","g"], "ansible_post_tasks": [], "ansible_environment": {}}),
                # Check ansible_post_tasks using defaults or env vars
                ({"ansible_post_tasks": ""}, {}, {"ansible_pre_tasks": [], "ansible_post_tasks": [], "ansible_environment": {}}),
                ({"ansible_post_tasks": None}, {}, {"ansible_pre_tasks": [], "ansible_post_tasks": [], "ansible_environment": {}}),
                ({"ansible_post_tasks": "a"}, {}, {"ansible_pre_tasks": [], "ansible_post_tasks": ["a"], "ansible_environment": {}}),
                ({"ansible_post_tasks": ["a"]}, {}, {"ansible_pre_tasks": [], "ansible_post_tasks": ["a"], "ansible_environment": {}}),
                ({"ansible_post_tasks": "a,b,c"}, {}, {"ansible_pre_tasks": [], "ansible_post_tasks": ["a","b","c"], "ansible_environment": {}}),
                ({"ansible_post_tasks": ["a","b","c"]}, {}, {"ansible_pre_tasks": [], "ansible_post_tasks": ["a","b","c"], "ansible_environment": {}}),
                ({}, {"SPLUNK_ANSIBLE_POST_TASKS": "d"}, {"ansible_pre_tasks": [], "ansible_post_tasks": ["d"], "ansible_environment": {}}),
                ({}, {"SPLUNK_ANSIBLE_POST_TASKS": "e,f,g"}, {"ansible_pre_tasks": [], "ansible_post_tasks": ["e","f","g"], "ansible_environment": {}}),
                ({"ansible_post_tasks": "a,b,c"}, {"SPLUNK_ANSIBLE_POST_TASKS": "e,f,g"}, {"ansible_pre_tasks": [], "ansible_post_tasks": ["e","f","g"], "ansible_environment": {}}),
                ({"ansible_post_tasks": ["a","b","c"]}, {"SPLUNK_ANSIBLE_POST_TASKS": "e,f,g"}, {"ansible_pre_tasks": [], "ansible_post_tasks": ["e","f","g"], "ansible_environment": {}}),
                # Check ansible_environment using defaults or env vars
                ({"ansible_environment": None}, {}, {"ansible_pre_tasks": [], "ansible_post_tasks": [], "ansible_environment": {}}),
                ({"ansible_environment": {"a": "b"}}, {}, {"ansible_pre_tasks": [], "ansible_post_tasks": [], "ansible_environment": {"a": "b"}}),
                ({"ansible_environment": {"a": "b", "d": "e"}}, {}, {"ansible_pre_tasks": [], "ansible_post_tasks": [], "ansible_environment": {"a": "b", "d": "e"}}),
                ({}, {"SPLUNK_ANSIBLE_ENV": "a=b"}, {"ansible_pre_tasks": [], "ansible_post_tasks": [], "ansible_environment": {"a": "b"}}),
                ({}, {"SPLUNK_ANSIBLE_ENV": "a=b,x=y"}, {"ansible_pre_tasks": [], "ansible_post_tasks": [], "ansible_environment": {"a": "b", "x": "y"}}),
                ({"ansible_environment": {"a": "c", "d": "e"}}, {"SPLUNK_ANSIBLE_ENV": "a=b,x=y"}, {"ansible_pre_tasks": [], "ansible_post_tasks": [], "ansible_environment": {"a": "b", "d": "e", "x": "y"}}),
            ]
        )
def test_getAnsibleContext(default_yml, os_env, output):
    vars_scope = default_yml
    with patch("environ.inventory") as mock_inven:
        with patch("os.environ", new=os_env):
            environ.getAnsibleContext(vars_scope)
    assert vars_scope == output

@pytest.mark.parametrize(("default_yml", "os_env", "splunk_asan"),
            [
                # Check null parameters
                ({}, {}, False),
                # Check default.yml parameters
                ({"asan": False}, {}, False),
                ({"asan": True}, {}, True),
                # Check env var parameters
                ({}, {"SPLUNK_ENABLE_ASAN": ""}, False),
                ({}, {"SPLUNK_ENABLE_ASAN": "anything"}, True),
                # Check both
                ({"asan": False}, {"SPLUNK_ENABLE_ASAN": ""}, False),
                ({"asan": True}, {"SPLUNK_ENABLE_ASAN": ""}, False),
                ({"asan": True}, {"SPLUNK_ENABLE_ASAN": "true"}, True),
                ({"asan": False}, {"SPLUNK_ENABLE_ASAN": "yes"}, True),
            ]
        )
def test_getASan(default_yml, os_env, splunk_asan):
    vars_scope = {"ansible_environment": {}, "splunk": {}}
    vars_scope["splunk"] = default_yml
    with patch("environ.inventory") as mock_inven:
        with patch("os.environ", new=os_env):
            environ.getASan(vars_scope)
    assert vars_scope["splunk"]["asan"] == splunk_asan
    if vars_scope["splunk"]["asan"]:
        assert vars_scope["ansible_environment"].get("ASAN_OPTIONS") == "detect_leaks=0"
    else:
        assert vars_scope["ansible_environment"].get("ASAN_OPTIONS") == None

@pytest.mark.parametrize(("default_yml", "os_env", "result"),
            [
                # Check null parameters
                ({}, {}, {"enable": True, "port": 8088, "token": None, "ssl": True}),
                # Check default.yml parameters
                ({"enable": False}, {}, {"enable": False, "port": 8088, "token": None, "ssl": True}),
                ({"port": 8099}, {}, {"enable": True, "port": 8099, "token": None, "ssl": True}),
                ({"token": "abcd"}, {}, {"enable": True, "port": 8088, "token": "abcd", "ssl": True}),
                ({"ssl": False}, {}, {"enable": True, "port": 8088, "token": None, "ssl": False}),
                # Check env var parameters
                ({}, {"SPLUNK_HEC_TOKEN": "qwerty"}, {"enable": True, "port": 8088, "token": "qwerty", "ssl": True}),
                ({}, {"SPLUNK_HEC_PORT": "9999"}, {"enable": True, "port": 9999, "token": None, "ssl": True}),
                ({}, {"SPLUNK_HEC_SSL": "true"}, {"enable": True, "port": 8088, "token": None, "ssl": True}),
                ({}, {"SPLUNK_HEC_SSL": "false"}, {"enable": True, "port": 8088, "token": None, "ssl": False}),
                ({}, {"SPLUNK_HEC_SSL": "FALSE"}, {"enable": True, "port": 8088, "token": None, "ssl": False}),
                # Check both
                ({"port": 8099}, {"SPLUNK_HEC_PORT": "19999"}, {"enable": True, "port": 19999, "token": None, "ssl": True}),
                ({"token": "abcd"}, {"SPLUNK_HEC_TOKEN": "fdsa"}, {"enable": True, "port": 8088, "token": "fdsa", "ssl": True}),
                ({"ssl": True}, {"SPLUNK_HEC_SSL": "fAlSe"}, {"enable": True, "port": 8088, "token": None, "ssl": False}),
            ]
        )
def test_getHEC(default_yml, os_env, result):
    vars_scope = {"splunk": {}}
    vars_scope["splunk"] = {
        "hec": {
            "enable": True,
            "port": 8088,
            "token": None,
            "ssl": True
        }
    }
    vars_scope["splunk"]["hec"].update(default_yml)
    with patch("environ.inventory") as mock_inven:
        with patch("os.environ", new=os_env):
            environ.getHEC(vars_scope)
    assert vars_scope["splunk"]["hec"] == result

@pytest.mark.parametrize(("default_yml", "os_env", "result"),
            [
                # Check null parameters
                ({}, {}, False),
                # # Check default.yml parameters
                ({"disable_popups": False}, {}, False),
                ({"disable_popups": True}, {}, True),
                # # Check env var parameters
                ({}, {"SPLUNK_DISABLE_POPUPS": "TRUE"}, True),
                ({}, {"SPLUNK_DISABLE_POPUPS": "true"}, True),
                ({}, {"SPLUNK_DISABLE_POPUPS": "True"}, True),
                ({}, {"SPLUNK_DISABLE_POPUPS": "false"}, False),
                ({}, {"SPLUNK_DISABLE_POPUPS": "False"}, False),
                ({}, {"SPLUNK_DISABLE_POPUPS": "FALSE"}, False),
                # # Check both
                ({"disable_popups": False}, {"SPLUNK_DISABLE_POPUPS": "TRUE"}, True),
                ({"disable_popups": False}, {"SPLUNK_DISABLE_POPUPS": "True"}, True),
                ({"disable_popups": True}, {"SPLUNK_DISABLE_POPUPS": "False"}, False),
                ({"disable_popups": True}, {"SPLUNK_DISABLE_POPUPS": "FALSE"}, False),
            ]
        )
def test_getDisablePopups(default_yml, os_env, result):
    vars_scope = {}
    vars_scope["splunk"] = default_yml
    with patch("environ.inventory") as mock_inven:
        with patch("os.environ", new=os_env):
            environ.getDisablePopups(vars_scope)
    assert vars_scope["splunk"]["disable_popups"] == result

@pytest.mark.parametrize(("default_yml", "os_env", "result"),
            [
                # Check null parameters
                ({}, {}, {"enable": False, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                # Check default.yml parameters
                ({"enable": True}, {}, {"enable": True, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({"server": "fwd.dsp.com:8888"}, {}, {"enable": False, "server": "fwd.dsp.com:8888", "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({"cert": "path/to/cert.pem"}, {}, {"enable": False, "server": None, "cert": "path/to/cert.pem", "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({"verify": True}, {}, {"enable": False, "server": None, "cert": None, "verify": True, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({"pipeline_name": "abcd"}, {}, {"enable": False, "server": None, "cert": None, "verify": False, "pipeline_name": "abcd", "pipeline_desc": None, "pipeline_spec": None}),
                ({"pipeline_desc": "abcd"}, {}, {"enable": False, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": "abcd", "pipeline_spec": None}),
                ({"pipeline_spec": "abcd"}, {}, {"enable": False, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": "abcd"}),
                # Check env var parameters
                ({}, {"SPLUNK_DSP_SERVER": "fwd.dsp.com:9999"}, {"enable": False, "server": "fwd.dsp.com:9999", "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({}, {"SPLUNK_DSP_CERT": "crt.pem"}, {"enable": False, "server": None, "cert": "crt.pem", "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({}, {"SPLUNK_DSP_VERIFY": "yes"}, {"enable": False, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({}, {"SPLUNK_DSP_VERIFY": "true"}, {"enable": False, "server": None, "cert": None, "verify": True, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({}, {"SPLUNK_DSP_VERIFY": "TRUE"}, {"enable": False, "server": None, "cert": None, "verify": True, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({}, {"SPLUNK_DSP_ENABLE": "yes"}, {"enable": False, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({}, {"SPLUNK_DSP_ENABLE": "true"}, {"enable": True, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({}, {"SPLUNK_DSP_ENABLE": "TRUE"}, {"enable": True, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({}, {"SPLUNK_DSP_PIPELINE_NAME": "do"}, {"enable": False, "server": None, "cert": None, "verify": False, "pipeline_name": "do", "pipeline_desc": None, "pipeline_spec": None}),
                ({}, {"SPLUNK_DSP_PIPELINE_DESC": "re"}, {"enable": False, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": "re", "pipeline_spec": None}),
                ({}, {"SPLUNK_DSP_PIPELINE_SPEC": "mi"}, {"enable": False, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": "mi"}),
                # Check both
                ({"enable": True}, {"SPLUNK_DSP_ENABLE": "false"}, {"enable": True, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({"enable": False}, {"SPLUNK_DSP_ENABLE": "true"}, {"enable": True, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({"server": "fwd.dsp.com:8888"}, {"SPLUNK_DSP_SERVER": "fwd.dsp.com:9999"}, {"enable": False, "server": "fwd.dsp.com:9999", "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({"cert": "path1/crt.pem"}, {"SPLUNK_DSP_CERT": "path2/cert.pem"}, {"enable": False, "server": None, "cert": "path2/cert.pem", "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({"verify": True}, {"SPLUNK_DSP_VERIFY": "false"}, {"enable": False, "server": None, "cert": None, "verify": True, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({"verify": False}, {"SPLUNK_DSP_VERIFY": "TRUE"}, {"enable": False, "server": None, "cert": None, "verify": True, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": None}),
                ({"pipeline_name": "abcd"}, {"SPLUNK_DSP_PIPELINE_NAME": "xyz"}, {"enable": False, "server": None, "cert": None, "verify": False, "pipeline_name": "xyz", "pipeline_desc": None, "pipeline_spec": None}),
                ({"pipeline_desc": "abcd"}, {"SPLUNK_DSP_PIPELINE_DESC": "xyz"}, {"enable": False, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": "xyz", "pipeline_spec": None}),
                ({"pipeline_spec": "abcd"}, {"SPLUNK_DSP_PIPELINE_SPEC": "xyz"}, {"enable": False, "server": None, "cert": None, "verify": False, "pipeline_name": None, "pipeline_desc": None, "pipeline_spec": "xyz"}),
            ]
        )
def test_getDSP(default_yml, os_env, result):
    vars_scope = {"splunk": {}}
    vars_scope["splunk"] = {
        "dsp": {
            "enable": False,
            "server": None,
            "cert": None,
            "verify": False,
            "pipeline_name": None,
            "pipeline_desc": None,
            "pipeline_spec": None,
        }
    }
    vars_scope["splunk"]["dsp"].update(default_yml)
    with patch("environ.inventory") as mock_inven:
        with patch("os.environ", new=os_env):
            environ.getDSP(vars_scope)
    assert vars_scope["splunk"]["dsp"] == result

@pytest.mark.parametrize(("es_enablement", "os_env", "result"),
            [
                (None, {}, ""),
                (None, {"SPLUNK_ES_SSL_ENABLEMENT":"strict"}, "--ssl_enablement strict"),
                ({"ssl_enablement":"auto"}, {}, "--ssl_enablement auto"),
                ({"ssl_enablement":"strict"}, {}, "--ssl_enablement strict"),
                ({"ssl_enablement":"ignore"}, {}, "--ssl_enablement ignore"),
                ({"ssl_enablement":"ignore"}, {"SPLUNK_ES_SSL_ENABLEMENT":"strict"}, "--ssl_enablement strict"),
                ({"ssl_enablement":"invalid"}, {}, "Exception")
            ]
        )
def test_getESSplunkVariables(es_enablement, os_env, result):
    vars_scope = {"splunk": {}}
    if es_enablement is not None:
        vars_scope["splunk"]["es"] = es_enablement
    with patch("environ.inventory") as mock_inven:
        with patch("os.environ", new=os_env):
            try:
                environ.getESSplunkVariables(vars_scope)
                assert vars_scope["es_ssl_enablement"] == result
            except Exception:
                assert result == "Exception"

@pytest.mark.parametrize(("os_env", "license_master_url", "deployer_url", "cluster_master_url", "search_head_captain_url"),
                         [
                            ({}, "", "", "", ""),
                            # Check individual environment variables
                            ({"SPLUNK_LICENSE_MASTER_URL": "something"}, "https://something:8089", "", "", ""),
                            ({"SPLUNK_DEPLOYER_URL": "something"}, "", "something", "", ""),
                            ({"SPLUNK_CLUSTER_MASTER_URL": "something"}, "", "", "something", ""),
                            ({"SPLUNK_SEARCH_HEAD_CAPTAIN_URL": "something"}, "", "", "", "something"),
                         ]
                        )
def test_getDistributedTopology(os_env, license_master_url, deployer_url, cluster_master_url, search_head_captain_url):
    vars_scope = {"splunk": {}}
    with patch("os.environ", new=os_env):
        environ.getDistributedTopology(vars_scope)
    assert type(vars_scope["splunk"]["license_master_url"]) == str
    assert vars_scope["splunk"]["license_master_url"] == license_master_url
    assert type(vars_scope["splunk"]["deployer_url"]) == str
    assert vars_scope["splunk"]["deployer_url"] == deployer_url
    assert type(vars_scope["splunk"]["cluster_master_url"]) == str
    assert vars_scope["splunk"]["cluster_master_url"] == cluster_master_url
    assert type(vars_scope["splunk"]["search_head_captain_url"]) == str
    assert vars_scope["splunk"]["search_head_captain_url"] == search_head_captain_url

@pytest.mark.parametrize(("default_yml", "os_env", "license_uri", "wildcard_license", "ignore_license", "license_download_dest"),
                         [
                            ({}, {}, "splunk.lic", False, False, "/tmp/splunk.lic"),
                            # Check individual environment variables
                            ({}, {"SPLUNK_LICENSE_URI": "http://web/license.lic"}, "http://web/license.lic", False, False, "/tmp/splunk.lic"),
                            ({}, {"SPLUNK_LICENSE_URI": "/mnt/*.lic"}, "/mnt/*.lic", True, False, "/tmp/splunk.lic"),
                            ({}, {"SPLUNK_NFR_LICENSE": "/mnt/nfr.lic"}, "splunk.lic", False, False, "/tmp/splunk.lic"),
                            ({}, {"SPLUNK_IGNORE_LICENSE": ""}, "splunk.lic", False, False, "/tmp/splunk.lic"),
                            ({}, {"SPLUNK_IGNORE_LICENSE": "true"}, "splunk.lic", False, True, "/tmp/splunk.lic"),
                            ({}, {"SPLUNK_IGNORE_LICENSE": "TRUE"}, "splunk.lic", False, True, "/tmp/splunk.lic"),
                            ({}, {"SPLUNK_IGNORE_LICENSE": "false"}, "splunk.lic", False, False, "/tmp/splunk.lic"),
                            ({}, {"SPLUNK_LICENSE_INSTALL_PATH": "/Downloads/"}, "splunk.lic", False, False, "/Downloads/"),
                            # Check default.yml
                            ({"license_uri": None}, {}, "splunk.lic", False, False, "/tmp/splunk.lic"),
                            ({"license_uri": ""}, {}, "splunk.lic", False, False, "/tmp/splunk.lic"),
                            ({"license_uri": "http://web/license.lic"}, {}, "http://web/license.lic", False, False, "/tmp/splunk.lic"),
                            ({"license_uri": "/mnt/*.lic"}, {}, "/mnt/*.lic", True, False, "/tmp/splunk.lic"),
                            ({"license_uri": "/mnt/nfr.lic"}, {}, "/mnt/nfr.lic", False, False, "/tmp/splunk.lic"),
                            ({"license_uri": "/mnt/1.lic"}, {"SPLUNK_LICENSE_URI": "/mnt/2.lic"}, "/mnt/2.lic", False, False, "/tmp/splunk.lic"),
                            ({"license_download_dest": None}, {}, "splunk.lic", False, False, "/tmp/splunk.lic"),
                            ({"license_download_dest": ""}, {}, "splunk.lic", False, False, "/tmp/splunk.lic"),
                            ({"license_download_dest": "/Downloads/splunk.lic"}, {}, "splunk.lic", False, False, "/Downloads/splunk.lic"),
                            ({"license_download_dest": "/Downloads/splunk.lic"}, {"SPLUNK_LICENSE_INSTALL_PATH": "/mnt/license.file"}, "splunk.lic", False, False, "/mnt/license.file"),
                         ]
                        )
def test_getLicenses(default_yml, os_env, license_uri, wildcard_license, ignore_license, license_download_dest):
    vars_scope = {"splunk": default_yml}
    with patch("os.environ", new=os_env):
        environ.getLicenses(vars_scope)
    assert vars_scope["splunk"]["license_uri"] == license_uri
    assert type(vars_scope["splunk"]["wildcard_license"]) == bool
    assert vars_scope["splunk"]["wildcard_license"] == wildcard_license
    assert type(vars_scope["splunk"]["ignore_license"]) == bool
    assert vars_scope["splunk"]["ignore_license"] == ignore_license
    assert vars_scope["splunk"]["license_download_dest"] == license_download_dest

@pytest.mark.parametrize(("default_yml", "os_env", "java_version", "java_download_url", "java_update_version"),
                         [
                            ({}, {}, None, None, None),
                            # Check environment variable parameters
                            ({}, {"JAVA": "oracle:8"}, None, None, None),
                            ({}, {"JAVA_VERSION": "openjdk:8"}, "openjdk:8", None, None),
                            ({}, {"JAVA_VERSION": "openjdk:9"}, "openjdk:9", None, None),
                            ({}, {"JAVA_VERSION": "oracle:8"}, "oracle:8", "https://download.oracle.com/otn-pub/java/jdk/8u141-b15/336fa29ff2bb4ef291e347e091f7f4a7/jdk-8u141-linux-x64.tar.gz", "141"),
                            ({}, {"JAVA_VERSION": "ORACLE:8"}, "oracle:8", "https://download.oracle.com/otn-pub/java/jdk/8u141-b15/336fa29ff2bb4ef291e347e091f7f4a7/jdk-8u141-linux-x64.tar.gz", "141"),
                            ({}, {"JAVA_VERSION": "openjdk:11"}, "openjdk:11", "https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_linux-x64_bin.tar.gz", "11.0.2"),
                            ({}, {"JAVA_VERSION": "oPenJdK:11"}, "openjdk:11", "https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_linux-x64_bin.tar.gz", "11.0.2"),
                            ({}, {"JAVA_VERSION": "oracle:8", "JAVA_DOWNLOAD_URL": "https://java/jdk-8u9000-linux-x64.tar.gz"}, "oracle:8", "https://java/jdk-8u9000-linux-x64.tar.gz", "9000"),
                            ({}, {"JAVA_VERSION": "openjdk:11", "JAVA_DOWNLOAD_URL": "https://java/openjdk-11.11.11_linux-x64_bin.tar.gz"}, "openjdk:11", "https://java/openjdk-11.11.11_linux-x64_bin.tar.gz", "11.11.11"),
                            # Check default.yml
                            ({"java_version": "openjdk:11"}, {}, "openjdk:11", None, None),
                            ({"java_download_url": "http://web/java.tgz"}, {}, None, "http://web/java.tgz", None),
                            ({"java_update_version": "jdk11u141"}, {}, None, None, "jdk11u141"),
                            # Check order of precedence
                            ({"java_version": "openjdk:9", "java_download_url": "http://web/java.tgz", "java_update_version": "jdk11u141"}, {"JAVA_VERSION": "oPenJdK:11"}, "openjdk:11", "https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_linux-x64_bin.tar.gz", "11.0.2"),
                         ]
                        )
def test_getJava(default_yml, os_env, java_version, java_download_url, java_update_version):
    vars_scope = default_yml
    with patch("os.environ", new=os_env):
        environ.getJava(vars_scope)
    assert vars_scope["java_version"] == java_version
    assert vars_scope["java_download_url"] == java_download_url
    assert vars_scope["java_update_version"] == java_update_version

@pytest.mark.parametrize(("os_env", "java_version", "java_download_url", "err_msg"),
    [
        ({"JAVA_VERSION": "oracle:3"}, None, None, "Invalid Java version supplied"),
        ({"JAVA_VERSION": "openjdk:20"}, None, None, "Invalid Java version supplied"),
        ({"JAVA_VERSION": "oracle:8", "JAVA_DOWNLOAD_URL": "https://java/jdk-8u9000.tar.gz"}, "oracle:8", "https://java/jdk-8u9000.tar.gz", "Invalid Java download URL format"),
        ({"JAVA_VERSION": "openjdk:11", "JAVA_DOWNLOAD_URL": "https://java/openjdk-11.tar.gz"}, "openjdk:11", "https://java/openjdk-11.tar.gz", "Invalid Java download URL format"),
    ]
)
def test_getJava_exception(os_env, java_version, java_download_url, err_msg):
    vars_scope = {"splunk": {}}
    with patch("os.environ", new=os_env):
        try:
            environ.getJava(vars_scope)
            assert False
        except Exception as e:
            assert True
            assert err_msg in str(e)
    assert vars_scope["java_version"] == java_version
    assert vars_scope["java_download_url"] == java_download_url
    assert vars_scope["java_update_version"] == None

@pytest.mark.parametrize(("default_yml", "os_env", "build", "build_url_bearer_token"),
                         [
                            ({}, {}, None, None),
                            # Check default.yml parameters
                            ({"buildlocation": "http://server/file.tgz"}, {}, None, None),
                            ({"build_location": None}, {}, None, None),
                            ({"build_location": ""}, {}, "", None),
                            ({"build_location": "/path/to/file.tgz"}, {}, "/path/to/file.tgz", None),
                            ({"build_location": "http://server/file.tgz"}, {}, "http://server/file.tgz", None),
                            ({"build_location": "https://server/file.tgz"}, {}, "https://server/file.tgz", None),
                            # Check environment variable parameters
                            ({}, {"SPLUNK_BUILD": "http://server/file.tgz"}, None, None),
                            ({}, {"SPLUNK_BUILD_URL": None}, None, None),
                            ({}, {"SPLUNK_BUILD_URL": ""}, "", None),
                            ({}, {"SPLUNK_BUILD_URL": "/path/to/file.tgz", "SPLUNK_BUILD_URL_BEARER_TOKEN": "testToken"}, "/path/to/file.tgz", "testToken"),
                            ({}, {"SPLUNK_BUILD_URL": "http://server/file.tgz", "SPLUNK_BUILD_URL_BEARER_TOKEN": "testToken"}, "http://server/file.tgz", "testToken"),
                            ({}, {"SPLUNK_BUILD_URL": "https://server/file.tgz", "SPLUNK_BUILD_URL_BEARER_TOKEN": "testToken"}, "https://server/file.tgz", "testToken"),
                            # Check order of precedence
                            ({"build_location": "http://server/file1.tgz"}, {"SPLUNK_BUILD_URL": "https://server/file2.tgz"}, "https://server/file2.tgz", None),
                            ({"build_location": "http://server/file1.tgz"}, {"SPLUNK_BUILD_URL": "/path/to/file.tgz"}, "/path/to/file.tgz", None),
                         ]
                        )
def test_getSplunkBuild(default_yml, os_env, build, build_url_bearer_token):
    vars_scope = dict()
    vars_scope["splunk"] = default_yml
    with patch("os.environ", new=os_env):
        environ.getSplunkBuild(vars_scope)
    assert vars_scope["splunk"]["build_location"] == build
    assert vars_scope["splunk"]["build_url_bearer_token"] == build_url_bearer_token

@pytest.mark.parametrize(("default_yml", "response_content", "trigger_splunkbase"),
                         [
                            ({}, "<id>123abc</id>", False),
                            ({"splunkbase_username": "ocho"}, "<id>123abc</id>", False),
                            ({"splunkbase_password": "cinco"}, "<id>123abc</id>", False),
                            ({"splunkbase_username": "ocho", "splunkbase_password": "cinco"}, "<id>123abc</id>", True),
                            ({"splunkbase_username": "", "splunkbase_password": ""}, "<id>123abc</id>", False),
                            ({}, "<id>123abc</id>", False),
                            ({"splunkbase_username": "ocho"}, b"<id>123abc</id>", False),
                            ({"splunkbase_password": "cinco"}, b"<id>123abc</id>", False),
                            ({"splunkbase_username": "ocho", "splunkbase_password": "cinco"}, b"<id>123abc</id>", True),
                            ({"splunkbase_username": "", "splunkbase_password": ""}, b"<id>123abc</id>", False),
                         ]
                        )
def test_getSplunkbaseToken(default_yml, response_content, trigger_splunkbase):
    vars_scope = default_yml
    with patch("environ.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, content=response_content)
        with patch("os.environ", new=dict()):
            environ.getSplunkbaseToken(vars_scope)
        # Make sure Splunkbase token is populated when appropriate
        assert "splunkbase_token" in vars_scope
        assert "splunkbase_username" in vars_scope
        assert "splunkbase_password" in vars_scope
        if trigger_splunkbase:
            mock_post.assert_called_with("https://splunkbase.splunk.com/api/account:login/", data={"username": "ocho", "password": "cinco"})
            assert vars_scope.get("splunkbase_token") == "123abc"
        else:
            mock_post.assert_not_called()
            assert not vars_scope.get("splunkbase_token")

def test_getSplunkbaseToken_exception():
    with patch("environ.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=400, content="error")
        try:
            environ.getSplunkbaseToken({"splunkbase_username": "ocho", "splunkbase_password": "cinco"})
            assert False
        except Exception as e:
            assert True
            assert "Invalid Splunkbase credentials" in str(e)

@pytest.mark.parametrize(("default_yml", "os_env", "apps_cnt_def", "apps_cnt_shc", "apps_cnt_idc"),
                         [
                            # Check null parameters
                            ({}, {}, 0, 0, 0),
                            # Check default.yml parameters
                            ({"app_paths_install": {"defaults": ["a"]}}, {}, 0, 0, 0),
                            ({"app_paths_install": {"default": ["a"]}}, {}, 1, 0, 0),
                            ({"apps_paths_install":{"default": ["a", "b", "c"]}}, {}, 0, 0, 0),
                            ({"app_paths_install": {"default": ["a", "b", "c"], "shc": ["e", "f"]}}, {}, 3, 2, 0),
                            ({"app_paths_install": {"default": ["a", "b", "c"], "idxc": ["e", "f"]}}, {}, 3, 0, 2),
                            ({"app_paths_install": {"shc": ["a", "b", "c"], "idxc": ["e", "f"]}}, {}, 0, 3, 2),
                            ({"app_paths_install": {"default": ["a"], "shc": ["b"], "idxc": ["c"]}}, {}, 1, 1, 1),
                         ]
                        )
def test_getSplunkAppPathInstall(default_yml, os_env, apps_cnt_def, apps_cnt_shc, apps_cnt_idc):
    vars_scope = dict()
    vars_scope["splunk"] = default_yml
    with patch("os.environ", new=os_env):
        environ.getSplunkAppPathInstall(vars_scope)
    assert type(vars_scope["splunk"]["app_paths_install"]["default"]) == list
    assert len(vars_scope["splunk"]["app_paths_install"]["default"]) == apps_cnt_def
    assert type(vars_scope["splunk"]["app_paths_install"]["shc"]) == list
    assert len(vars_scope["splunk"]["app_paths_install"]["shc"]) == apps_cnt_shc
    assert type(vars_scope["splunk"]["app_paths_install"]["idxc"]) == list
    assert len(vars_scope["splunk"]["app_paths_install"]["idxc"]) == apps_cnt_idc

@pytest.mark.parametrize(("default_yml", "os_env", "apps_count"),
                         [
                            # Check null parameters
                            ({}, {}, 0),
                            # Check default.yml parameters
                            ({"app_location": []}, {}, 0),
                            ({"app_location": ["a"]}, {}, 0),
                            ({"app_location": ["a", "b", "c"]}, {}, 0),
                            ({"apps_location": []}, {}, 0),
                            ({"apps_location": ["a"]}, {}, 1),
                            ({"apps_location": ["a", "b", "c"]}, {}, 3),
                            ({"apps_location": "a"}, {}, 1),
                            ({"apps_location": "a,b,c,d"}, {}, 4),
                            # Check environment variable parameters
                            ({}, {"SPLUNK_APPS": None}, 0),
                            ({}, {"SPLUNK_APPS": "hi"}, 0),
                            ({}, {"SPLUNK_APPS_URL": "hi"}, 1),
                            ({}, {"SPLUNK_APPS_URL": "a,b,ccccc,dd"}, 4),
                            # Check the union combination of default.yml + environment variables
                            ### Invalid 'app_location' variable name in default.yml
                            ({"app_location": []}, {"SPLUNK_APPS_URL": None}, 0),
                            ({"app_location": ["a"]}, {"SPLUNK_APPS_URL": "a"}, 1),
                            ({"app_location": ["a", "b", "c"]}, {"SPLUNK_APPS_URL": "a,bb"}, 2),
                            ### Invalid 'SPLUNK_APP_URL' variable name in env vars
                            ({"apps_location": ["x"]}, {"SPLUNK_APP_URL": "a"}, 1),
                            ({"apps_location": ["x", "y"]}, {"SPLUNK_APP_URL": "a,bb"}, 2),
                            ({"apps_location": "x,y,z"}, {"SPLUNK_APP_URL": "a,bb"}, 3),
                            ### Correct variable names
                            ({"apps_location": ["x"]}, {"SPLUNK_APPS_URL": "a"}, 2),
                            ({"apps_location": ["x", "y"]}, {"SPLUNK_APPS_URL": "a,bb"}, 4),
                            ({"apps_location": "x,y,z"}, {"SPLUNK_APPS_URL": "a,bb"}, 5),
                            ### Only return unique set of apps
                            ({"apps_location": ["x"]}, {"SPLUNK_APPS_URL": "x"}, 1),
                            ({"apps_location": ["x", "y"]}, {"SPLUNK_APPS_URL": "a,bb,y"}, 4),
                            ({"apps_location": "x,y,z"}, {"SPLUNK_APPS_URL": "x,yy,a,z"}, 5),
                         ]
                        )
def test_getSplunkApps(default_yml, os_env, apps_count):
    vars_scope = dict()
    vars_scope["splunk"] = default_yml
    with patch("os.environ", new=os_env):
        environ.getSplunkApps(vars_scope)
    assert type(vars_scope["splunk"]["apps_location"]) == list
    assert len(vars_scope["splunk"]["apps_location"]) == apps_count

@pytest.mark.parametrize(("default_yml", "os_env", "apps_count"),
                         [
                            # Check null parameters
                            ({}, {}, 0),
                            # Check default.yml parameters
                            ({"app_location_local": []}, {}, 0),
                            ({"app_location_local": ["a"]}, {}, 0),
                            ({"app_location_local": ["a", "b", "c"]}, {}, 0),
                            ({"apps_location_local": []}, {}, 0),
                            ({"apps_location_local": ["a"]}, {}, 1),
                            ({"apps_location_local": ["a", "b", "c"]}, {}, 3),
                            ({"apps_location_local": "a"}, {}, 1),
                            ({"apps_location_local": "a,b,c,d"}, {}, 4),
                            # Check the union combination of default.yml + environment variables
                            ### Invalid 'app_location' variable name in default.yml
                            ({"app_location_local": []}, {"SPLUNK_APPS_URL_LOCAL": None}, 0),
                            ({"app_location_local": ["a"]}, {"SPLUNK_APPS_URL_LOCAL": "a"}, 1),
                            ({"app_location_local": ["a", "b", "c"]}, {"SPLUNK_APPS_URL_LOCAL": "a,bb"}, 2),
                            ### Invalid 'SPLUNK_APP_URL' variable name in env vars
                            ({"apps_location_local": ["x"]}, {"SPLUNK_APP_URL_LOCAL": "a"}, 1),
                            ({"apps_location_local": ["x", "y"]}, {"SPLUNK_APP_URL_LOCAL": "a,bb"}, 2),
                            ({"apps_location_local": "x,y,z"}, {"SPLUNK_APP_URL_LOCAL": "a,bb"}, 3),
                            ### Correct variable names
                            ({"apps_location_local": ["x"]}, {"SPLUNK_APPS_URL_LOCAL": "a"}, 2),
                            ({"apps_location_local": ["x", "y"]}, {"SPLUNK_APPS_URL_LOCAL": "a,bb"}, 4),
                            ({"apps_location_local": "x,y,z"}, {"SPLUNK_APPS_URL_LOCAL": "a,bb"}, 5),
                            ### Only return unique set of apps
                            ({"apps_location_local": ["x"]}, {"SPLUNK_APPS_URL_LOCAL": "x"}, 1),
                            ({"apps_location_local": ["x", "y"]}, {"SPLUNK_APPS_URL_LOCAL": "a,bb,y"}, 4),
                            ({"apps_location_local": "x,y,z"}, {"SPLUNK_APPS_URL_LOCAL": "x,yy,a,z"}, 5),
                         ]
                        )
def test_getSplunkAppsLocal(default_yml, os_env, apps_count):
    vars_scope = dict()
    vars_scope["splunk"] = default_yml
    with patch("os.environ", new=os_env):
        environ.getSplunkAppsLocal(vars_scope)
    assert type(vars_scope["splunk"]["apps_location_local"]) == list
    assert len(vars_scope["splunk"]["apps_location_local"]) == apps_count

@pytest.mark.parametrize(("default_yml", "os_env", "key", "value"),
            [
                # Check cert_prefix
                ({}, {}, "cert_prefix", "https"),
                ({"cert_prefix": "http"}, {}, "cert_prefix", "http"),
                ({}, {"SPLUNK_CERT_PREFIX": "fakehttps"}, "cert_prefix", "fakehttps"),
                # Check splunk.user
                ({"splunk": {"user": "root"}}, {}, "splunk.user", "root"),
                ({}, {"SPLUNK_USER": "root"}, "splunk.user", "root"),
                # Check splunk.group
                ({"splunk": {"group": "root"}}, {}, "splunk.group", "root"),
                ({}, {"SPLUNK_GROUP": "root"}, "splunk.group", "root"),
                # Check splunk.root_endpoint
                ({"splunk": {"root_endpoint": "/splunk"}}, {}, "splunk.root_endpoint", "/splunk"),
                ({}, {"SPLUNK_ROOT_ENDPOINT": "/splk"}, "splunk.root_endpoint", "/splk"),
                # Check splunk.svc_port
                ({"splunk": {"svc_port": "9089"}}, {}, "splunk.svc_port", "9089"),
                ({}, {"SPLUNK_SVC_PORT": "8189"}, "splunk.svc_port", "8189"),
                # Check splunk.s2s.port
                ({"splunk": {"s2s": {"port": "9999"}}}, {}, "splunk.s2s.port", 9999),
                ({}, {"SPLUNK_S2S_PORT": "9991"}, "splunk.s2s.port", 9991),
                # Check splunk.enable_service
                ({"splunk": {"enable_service": "yes"}}, {}, "splunk.enable_service", "yes"),
                ({}, {"SPLUNK_ENABLE_SERVICE": "no"}, "splunk.enable_service", "no"),
                # Check splunk.service_name
                ({"splunk": {"service_name": "SpLuNkD"}}, {}, "splunk.service_name", "SpLuNkD"),
                ({}, {"SPLUNK_SERVICE_NAME": "sPlUnKd"}, "splunk.service_name", "sPlUnKd"),
                # Check splunk.allow_upgrade
                ({"splunk": {"allow_upgrade": "yes"}}, {}, "splunk.allow_upgrade", "yes"),
                ({}, {"SPLUNK_ALLOW_UPGRADE": "no"}, "splunk.allow_upgrade", "no"),
                # Check splunk.set_search_peers
                ({"splunk": {"set_search_peers": False}}, {}, "splunk.set_search_peers", False),
                ({}, {"SPLUNK_SET_SEARCH_PEERS": "False"}, "splunk.set_search_peers", False),
                ({"splunk": {"set_search_peers": True}}, {"SPLUNK_SET_SEARCH_PEERS": "False"}, "splunk.set_search_peers", False),
                # Check splunk.appserver.port
                ({"splunk": {"appserver": {"port": "9291"}}}, {}, "splunk.appserver.port", "9291"),
                ({}, {"SPLUNK_APPSERVER_PORT": "9391"}, "splunk.appserver.port", "9391"),
                # Check splunk.kvstore.port
                ({"splunk": {"kvstore" :{"port": "9165"}}}, {}, "splunk.kvstore.port", "9165"),
                ({}, {"SPLUNK_KVSTORE_PORT": "9265"}, "splunk.kvstore.port", "9265"),
                # Check splunk.connection_timeout
                ({"splunk": {"connection_timeout": 60}}, {}, "splunk.connection_timeout", 60),
                ({}, {"SPLUNK_CONNECTION_TIMEOUT": 200}, "splunk.connection_timeout", 200),
            ]
        )
def test_overrideEnvironmentVars(default_yml, os_env, key, value):
    vars_scope = {
                    "ansible_pre_tasks": None,
                    "ansible_post_tasks": None,
                    "cert_prefix": "https",
                    "splunk": {
                                "user": "splunk",
                                "group": "splunk",
                                "root_endpoint": None,
                                "svc_port": 8089,
                                "s2s": {"port": 9997},
                                "appserver": {"port": 8065},
                                "kvstore": {"port": 8191},
                                "hec_token": "abcd1234",
                                "enable_service": False,
                                "service_name": "Splunkd",
                                "allow_upgrade": True,
                                "asan": None,
                                "set_search_peers": True,
                                "connection_timeout": 0,
                            }
                }
    # TODO: Possibly remove the dependency on merge_dict() in this test
    environ.merge_dict(vars_scope, default_yml)
    with patch("os.environ", new=os_env):
        environ.overrideEnvironmentVars(vars_scope)
    if "splunk" in key:
        if "s2s" in key or "appserver" in key or "kvstore" in key:
            section, key = key.split(".")[-2:]
            assert vars_scope["splunk"][section][key] == value
        else:
            key = key.split(".")[-1]
            assert vars_scope["splunk"][key] == value
    else:
        assert vars_scope[key] == value

@pytest.mark.parametrize(("default_yml", "os_env", "output"),
            [
                # Check null parameters
                ({}, {}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                # Check default.yml parameters
                ({"dfs": {"enable": True}}, {}, {"enable": True, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({"dfs": {"dfw_num_slots": 20}}, {}, {"enable": False, "dfw_num_slots": 20, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({"dfs": {"dfw_num_slots": "15"}}, {}, {"enable": False, "dfw_num_slots": 15, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({"dfs": {"dfc_num_slots": 20}}, {}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 20, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({"dfs": {"dfc_num_slots": "15"}}, {}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 15, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({"dfs": {"dfw_num_slots_enabled": True}}, {}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": True, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({"dfs": {"spark_master_host": "10.0.0.1"}}, {}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "10.0.0.1", "spark_master_webui_port": 8080}),
                ({"dfs": {"spark_master_webui_port": 8081}}, {}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8081}),
                ({"dfs": {"spark_master_webui_port": "8082"}}, {}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8082}),
                # Check environment variable parameters
                ({}, {"SPLUNK_ENABLE_DFS": ""}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({}, {"SPLUNK_ENABLE_DFS": "true"}, {"enable": True, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({}, {"SPLUNK_ENABLE_DFS": "TRUE"}, {"enable": True, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({}, {"SPLUNK_DFW_NUM_SLOTS": "11"}, {"enable": False, "dfw_num_slots": 11, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({}, {"SPLUNK_DFC_NUM_SLOTS": "1"}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 1, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({}, {"SPLUNK_DFW_NUM_SLOTS_ENABLED": ""}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({}, {"SPLUNK_DFW_NUM_SLOTS_ENABLED": "true"}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": True, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({}, {"SPLUNK_DFW_NUM_SLOTS_ENABLED": "TRUE"}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": True, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({}, {"SPARK_MASTER_HOST": "8.8.8.8"}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "8.8.8.8", "spark_master_webui_port": 8080}),
                ({}, {"SPARK_MASTER_WEBUI_PORT": "8888"}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8888}),
                # Check the union combination of default.yml + environment variables and order of precedence when overwriting
                ({"dfs": {"enable": False}}, {"SPLUNK_ENABLE_DFS": "true"}, {"enable": True, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({"dfs": {"dfw_num_slots": 100}}, {"SPLUNK_DFW_NUM_SLOTS": "101"}, {"enable": False, "dfw_num_slots": 101, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({"dfs": {"dfc_num_slots": 100}}, {"SPLUNK_DFC_NUM_SLOTS": "101"}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 101, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({"dfs": {"dfw_num_slots_enabled": False}}, {"SPLUNK_DFW_NUM_SLOTS_ENABLED": "True"}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": True, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8080}),
                ({"dfs": {"spark_master_host": "10.0.0.1"}}, {"SPARK_MASTER_HOST": "8.8.8.8"}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "8.8.8.8", "spark_master_webui_port": 8080}),
                ({"dfs": {"spark_master_webui_port": 8082}}, {"SPARK_MASTER_WEBUI_PORT": "8888"}, {"enable": False, "dfw_num_slots": 10, "dfc_num_slots": 4, "dfw_num_slots_enabled": False, "spark_master_host": "127.0.0.1", "spark_master_webui_port": 8888}),
            ]
        )
def test_getDFS(default_yml, os_env, output):
    vars_scope = dict()
    vars_scope["splunk"] = default_yml
    with patch("os.environ", new=os_env):
        environ.getDFS(vars_scope)
    # Check typing
    assert type(vars_scope["splunk"]["dfs"]["enable"]) == bool
    assert type(vars_scope["splunk"]["dfs"]["dfw_num_slots"]) == int
    assert type(vars_scope["splunk"]["dfs"]["dfc_num_slots"]) == int
    assert type(vars_scope["splunk"]["dfs"]["dfw_num_slots_enabled"]) == bool
    assert type(vars_scope["splunk"]["dfs"]["spark_master_webui_port"]) == int
    assert vars_scope["splunk"]["dfs"] == output

@pytest.mark.parametrize(("os_env", "deployment_server", "deployment_client", "add", "before_start_cmd", "cmd"),
                         [
                            ({}, None, None, None, None, None),
                            # Check environment variable parameters
                            ({"SPLUNK_DEPLOYMENT_SERVER": ""}, None, None, None, None, None),
                            ({"SPLUNK_DEPLOYMENT_SERVER": "something"}, "something", None, None, None, None),
                            ({"SPLUNK_DEPLOYMENT_CLIENT_NAME": ""}, None, None, None, None, None),
                            ({"SPLUNK_DEPLOYMENT_CLIENT_NAME": "client_name"}, None, {"name": "client_name"}, None, None, None),
                            ({"SPLUNK_ADD": ""}, None, None, None, None, None),
                            ({"SPLUNK_ADD": "echo 1"}, None, None, ["echo 1"], None, None),
                            ({"SPLUNK_ADD": "echo 1,echo 2"}, None, None, ["echo 1", "echo 2"], None, None),
                            ({"SPLUNK_BEFORE_START_CMD": ""}, None, None, None, None, None),
                            ({"SPLUNK_BEFORE_START_CMD": "echo 1"}, None, None, None, ["echo 1"], None),
                            ({"SPLUNK_BEFORE_START_CMD": "echo 1,echo 2"}, None, None, None, ["echo 1", "echo 2"], None),
                            ({"SPLUNK_CMD": ""}, None, None, None, None, None),
                            ({"SPLUNK_CMD": "echo 1"}, None, None, None, None, ["echo 1"]),
                            ({"SPLUNK_CMD": "echo 1,echo 2"}, None, None, None, None, ["echo 1", "echo 2"]),
                         ]
                        )
def test_getUFSplunkVariables(os_env, deployment_server, deployment_client, add, before_start_cmd, cmd):
    vars_scope = {"splunk": {}}
    with patch("os.environ", new=os_env):
        environ.getUFSplunkVariables(vars_scope)
    assert vars_scope["splunk"].get("deployment_server") == deployment_server
    assert vars_scope["splunk"].get("deployment_client") == deployment_client
    assert vars_scope["splunk"].get("add") == add
    assert vars_scope["splunk"].get("before_start_cmd") == before_start_cmd
    assert vars_scope["splunk"].get("cmd") == cmd

def test_getRandomString():
    word = environ.getRandomString()
    assert len(word) == 6


@pytest.mark.parametrize(("url", "vars_scope", "output"),
            [
                ("licmaster", {"splunk": {}}, "https://licmaster:8089"),
                ("http://licmaster", {"splunk": {}}, "http://licmaster:8089"),
                ("licmaster:8081", {"splunk": {}}, "https://licmaster:8081"),
                ("http://licmaster:80", {"splunk": {}}, "http://licmaster:80"),
                ("ftp://licmaster.corp.net:3333", {"splunk": {}}, "ftp://licmaster.corp.net:3333"),
                ("username:password@lm.internal.net", {"splunk": {}}, "https://lm.internal.net:8089"),
                ("http://username:password@lm.internal.net:3333", {"splunk": {}}, "http://lm.internal.net:3333"),
                # Check null input
                ("", {"splunk": {}}, ""),
                (None, {"splunk": {}}, ""),
                # Check vars_scope overrides
                ("licmaster", {"cert_prefix": "http", "splunk": {"svc_port": 18089}}, "http://licmaster:18089"),
                ("https://licmaster", {"cert_prefix": "http", "splunk": {"svc_port": 18089}}, "https://licmaster:18089"),
                ("licmaster:28089", {"cert_prefix": "http", "splunk": {"svc_port": 18089}}, "http://licmaster:28089"),
                ("https://licmaster:38089", {"cert_prefix": "http", "splunk": {"svc_port": 18089}}, "https://licmaster:38089"),
            ]
        )
def test_parseUrl(url, vars_scope, output):
    result = environ.parseUrl(url, vars_scope)
    assert result == output

@pytest.mark.parametrize(("dict1", "dict2", "result"),
    [
        # Check dicts
        ({}, {"a": 2}, {"a": 2}),
        ({"b": 2}, {"a": 2}, {"a": 2, "b": 2}),
        ({"a": 1, "b": 2}, {"a": 2}, {"a": 2, "b": 2}),
        ({"a": 0}, {"a": 1}, {"a": 1}),
        ({"a": 1}, {"b": 2, "c": 3}, {"a": 1, "b": 2, "c": 3}),
        # Check arrays
        ({}, {"a": []}, {"a": []}),
        ({}, {"a": [1, 2]}, {"a": [1, 2]}),
        ({"b": [0]}, {"a": [1]}, {"a": [1], "b": [0]}),
        ({"a": [0]}, {"a": [1]}, {"a": [0, 1]}),
        # Check nested dict output
        ({"nested": {}}, {"nested": {"a": 1}}, {"nested": {"a": 1}}),
        ({"nested": {"a": 1}}, {"nested": {"b": 2}}, {"nested": {"a": 1, "b": 2}}),
        ({"nested": {"a": 1, "c": 3}}, {"nested": {"b": 2}}, {"nested": {"a": 1, "b": 2, "c": 3}}),
        ({"nested": {"a": 1, "b": 3}}, {"nested": {"b": 2}}, {"nested": {"a": 1, "b": 2}}),
        # Check nested with diff value types
        ({"nested": {"x": 1}}, {"nested": {"x": {"a": 1}}}, {"nested": {"x": {"a": 1}}}),
        ({"nested": {"x": {"a": 1}}}, {"nested": {"x": 1}}, {"nested": {"x": 1}}),
        # Check nested arrays
        ({"nested": {"array": []}}, {"nested": {"array": [1]}}, {"nested": {"array": [1]}}),
        ({"nested": {"array": [1, 2, 3]}}, {"nested": {"array": []}}, {"nested": {"array": [1, 2, 3]}}),
        ({"nested": {"array": [1, 2]}}, {"nested": {"array": [3, 4, 5]}}, {"nested": {"array": [1, 2, 3, 4, 5]}}),
        ({"nested": {"x": 10, "array": [1, 2]}}, {"nested": {"y": 20, "array": [3, 4, 5]}}, {"nested": {"x": 10, "y": 20, "array": [1, 2, 3, 4, 5]}}),
        # Targeted github bug
        ({"splunk": {"conf": [{"key": "fileA", "content": {"a": "b", "c": "d"}}]}}, {"splunk": {"conf": [{"key": "fileB", "content": {"e": "f", "g": "h"}}]}}, {"splunk": {"conf": [{"key": "fileA", "content": {"a": "b", "c": "d"}}, {"key": "fileB", "content": {"e": "f", "g": "h"}}]}}),
    ]
)
def test_merge_dict(dict1, dict2, result):
    output = environ.merge_dict(dict1, dict2)
    assert output == result

@pytest.mark.parametrize(("source", "merge_url_called", "merge_file_called"),
            [
                (None, False, False),
                ("", False, False),
                ("    ", False, False),
                ("http://web/default.yml", True, False),
                ("https://web/default.yml", True, False),
                ("file:///path/to/default.yml", False, True),
                ("/path/to/default.yml", False, True),
                ("rel/path/to/default.yml", False, True),
            ]
        )
def test_mergeDefaults(source, merge_url_called, merge_file_called):
    with patch("environ.mergeDefaultsFromFile") as mock_merge_file:
        with patch("environ.mergeDefaultsFromURL") as mock_merge_url:
            result = environ.mergeDefaults({"hello": "world"}, "foobar", source)
            if merge_url_called:
                mock_merge_url.assert_called_once()
                mock_merge_file.assert_not_called()
            else:
                mock_merge_url.assert_not_called()
            if merge_file_called:
                mock_merge_file.assert_called_once()
                mock_merge_url.assert_not_called()
            else:
                mock_merge_file.assert_not_called()

@pytest.mark.parametrize(("key"),
            [
                ("FOO"),
                ("BAR"),
                ("BAZ"),
            ]
        )
def test_mergeDefaults_url_with_req_params(key):
    config = {
                "config": {
                    "FOO": {
                        "headers": {"HI": "MOM"},
                        "verify": True
                    },
                    "BAR": {
                        "headers": {"GOODBYE": "MOM"},
                        "verify": False
                    }
                }
            }
    with patch("environ.mergeDefaultsFromFile") as mock_merge_file:
        with patch("environ.mergeDefaultsFromURL") as mock_merge_url:
            result = environ.mergeDefaults(config, key, "http://website/default.yml")
            mock_merge_file.assert_not_called()
            mock_merge_url.assert_called_once()
            if key == "FOO":
                mock_merge_url.assert_called_with(config, "http://website/default.yml", {"HI": "MOM"}, True)
            elif key == "BAR":
                mock_merge_url.assert_called_with(config, "http://website/default.yml", {"GOODBYE": "MOM"}, False)
            else:
                mock_merge_url.assert_called_with(config, "http://website/default.yml", None, False)

@pytest.mark.parametrize(("vars_scope", "content", "os_env", "headers", "verify"),
    [
        # Check dicts
        ({"config": {"max_retries": 3, "max_delay": 4, "max_timeout": 5}}, "helloworld", {}, None, False),
        # Change max_timeout
        ({"config": {"max_retries": 3, "max_delay": 4, "max_timeout": 11}}, "helloworld", {}, None, False),
        # Enable verify
        ({"config": {"max_retries": 3, "max_delay": 4, "max_timeout": 5}}, "helloworld", {}, None, True),
        # Exercise bytes content
        ({"config": {"max_retries": 3, "max_delay": 4, "max_timeout": 5}}, b"helloworld", {}, None, False),
        # Exercise various headers
        ({"config": {"max_retries": 3, "max_delay": 4, "max_timeout": 5}}, "helloworld", {}, {}, False),
        ({"config": {"max_retries": 3, "max_delay": 4, "max_timeout": 5}}, "helloworld", {}, {"HELLO": "WORLD"}, False),
        ({"config": {"max_retries": 3, "max_delay": 4, "max_timeout": 5}}, "helloworld", {}, {"A": "B", "C": "D"}, False),
        # Exercise OS env vars with headers
        ({"config": {"max_retries": 3, "max_delay": 4, "max_timeout": 5}}, "helloworld", {"one": "two"}, {}, False),
        ({"config": {"max_retries": 3, "max_delay": 4, "max_timeout": 5}}, "helloworld", {"SPLUNK_DEFAULTS_HTTP_AUTH_HEADER": "Bearer xyz"}, {"HELLO": "WORLD"}, False),
    ]
)
def test_mergeDefaultsFromURL(vars_scope, content, os_env, headers, verify):
    # Mock response
    mock_response = MagicMock()
    mock_response.content = "helloworld"
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    # Invoke function
    with patch("os.environ", new=os_env):
        with patch("environ.merge_dict") as mock_merge:
            with patch("environ.requests.get") as mock_get:
                mock_get.return_value = mock_response
                result = environ.mergeDefaultsFromURL(vars_scope, "http://website", headers, verify)
    # Check headers and parameters send to GET call
    expected_headers = {}
    if headers:
        expected_headers.update(headers)
    if os_env and "SPLUNK_DEFAULTS_HTTP_AUTH_HEADER" is os_env:
        expected_headers["Authorization"] = os_env["SPLUNK_DEFAULTS_HTTP_AUTH_HEADER"]
    mock_get.assert_called_once()
    mock_get.assert_called_with("http://website", headers=expected_headers, timeout=vars_scope["config"]["max_timeout"], verify=verify)
    mock_merge.assert_called_once()
    mock_merge.assert_called_with(vars_scope, "helloworld")

@pytest.mark.parametrize(("file", "file_exists", "merge_called"),
            [
                (None, False, False),
                ("", False, False),
                ("    ", False, False),
                ("/path/to/file", False, False),
                ("/path/to/file", True, True),
            ]
        )
def test_mergeDefaultsFromFile(file, file_exists, merge_called):
    mo = mock_open()
    with patch("environ.open", mo, create=True):
        with patch("environ.os") as mock_os:
            with patch("environ.merge_dict") as mock_merge:
                mock_os.path.exists = MagicMock(return_value=file_exists)
                result = environ.mergeDefaultsFromFile({"hello": "world"}, file)
                if merge_called:
                    mo.assert_called_once()
                    mock_merge.assert_called_once()
                else:
                    mo.assert_not_called()
                    mock_merge.assert_not_called()
                    assert result == {"hello": "world"}


@pytest.mark.parametrize(("mock_base", "mock_baked", "mock_env", "mock_host", "merge_call_count"),
            [
                # Null cases
                ({}, [], [], [], 0),
                ({"config": None}, [], [], [], 0),
                ({"config": {}}, [], [], [], 0),
                # Check baked
                ({"config": {"foo": "bar"}}, [{"key": "baked", "src": "file1"}], [], [], 1),
                ({"config": {"foo": "bar"}}, [{"key": "baked", "src": "f1"}, {"key": "baked", "src": "f2"}, {"key": "baked", "src": "f3"}], [], [], 3),
                # Check env
                ({"config": {"foo": "bar"}}, [], [{"key": "env", "src": "file1"}], [], 1),
                ({"config": {"foo": "bar"}}, [], [{"key": "env", "src": "f1"}, {"key": "env", "src": "f2"}, {"key": "env", "src": "f3"}], [], 3),
                # Check host
                ({"config": {"foo": "bar"}}, [], [], [{"key": "host", "src": "file1"}], 1),
                ({"config": {"foo": "bar"}}, [], [], [{"key": "host", "src": "f1"}, {"key": "host", "src": "f2"}, {"key": "host", "src": "f3"}], 3),
                # Check mixed
                ({"config": {"foo": "bar"}}, [{"key": "baked", "src": "file1"}], [{"key": "env", "src": "f1"}, {"key": "env", "src": "f2"}], [{"key": "host", "src": "f1"}, {"key": "host", "src": "f2"}], 5),
                ({"config": None}, [{"key": "baked", "src": "file1"}], [{"key": "env", "src": "f1"}, {"key": "env", "src": "f2"}], [{"key": "host", "src": "f1"}, {"key": "host", "src": "f2"}], 0),
                ({"config": {}}, [{"key": "baked", "src": "file1"}], [{"key": "env", "src": "f1"}, {"key": "env", "src": "f2"}], [{"key": "host", "src": "f1"}, {"key": "host", "src": "f2"}], 0),
            ]
        )
def test_loadDefaults(mock_base, mock_baked, mock_env, mock_host, merge_call_count):
    mbase = MagicMock(return_value=mock_base)
    mbaked = MagicMock(return_value=mock_baked)
    menv = MagicMock(return_value=mock_env)
    mhost = MagicMock(return_value=mock_host)
    with patch("environ.loadBaseDefaults", mbase):
        with patch("environ.loadBakedDefaults", mbaked):
            with patch("environ.loadEnvDefaults", menv):
                with patch("environ.loadHostDefaults", mhost):
                    with patch("environ.mergeDefaults") as mock_merge:
                        output = environ.loadDefaults()
                        assert mock_merge.call_count == merge_call_count

@pytest.mark.parametrize(("os_env", "filename"),
            [
                ({}, "splunk_defaults"),
                ({"SPLUNK_ROLE": "splunk_standalone"}, "splunk_defaults"),
                ({"SPLUNK_ROLE": "splunk_universal_forwarder"}, "splunkforwarder_defaults"),
            ]
        )
def test_loadBaseDefaults(os_env, filename):
    sample_yml = """
this: file
is:
    a: yaml
"""
    mo = mock_open(read_data=sample_yml)
    with patch("environ.open", mo, create=True):
        with patch("os.environ", new=os_env):
            output = environ.loadBaseDefaults()
        mo.assert_called_once()
        args, _ = mo.call_args
        assert filename in args[0]
        assert args[1] == "r"
    assert type(output) == dict
    assert output["this"] == "file"

@pytest.mark.parametrize(("config", "output"),
            [
                (None, []),
                ({}, []),
                ({"baked": None}, []),
                ({"baked": ""}, []),
                ({"baked": "file1"}, [{"key": "baked", "src": "file1"}]),
                ({"baked": "file1,file2,file3"}, [{"key": "baked", "src": "file1"}, {"key": "baked", "src": "file2"}, {"key": "baked", "src": "file3"}]),
            ]
        )
def test_loadBakedDefaults(config, output):
    result = environ.loadBakedDefaults(config)
    assert result == output

@pytest.mark.parametrize(("config", "output"),
            [
                (None, []),
                ({}, []),
                ({"env": None}, []),
                ({"env": {}}, []),
                ({"env": {"var": None}}, []),
                ({"env": {"var": ""}}, []),
                # Adding test for a key that does not exist
                ({"env": {"var": "FAKE"}}, []),
                # Adding tests for keys that exist
                ({"env": {"var": "KEY1"}}, [{"key": "env", "src": "file1"}]),
                ({"env": {"var": "KEY2"}}, [{"key": "env", "src": "file1"}, {"key": "env", "src": "file2"}, {"key": "env", "src": "file3"}]),
            ]
        )
def test_loadEnvDefaults(config, output):
    with patch("os.environ", new={"KEY1": "file1", "KEY2": "file1,file2,file3"}):
        result = environ.loadEnvDefaults(config)
    assert result == output

@pytest.mark.parametrize(("config", "output"),
            [
                (None, []),
                ({}, []),
                ({"host": None}, []),
                ({"host": {}}, []),
                ({"host": {"url": None}}, []),
                ({"host": {"url": ""}}, []),
                ({"host": {"url": "file1"}}, [{"key": "host", "src": "file1"}]),
                ({"host": {"url": "file1,file2,file3"}}, [{"key": "host", "src": "file1"}, {"key": "host", "src": "file2"}, {"key": "host", "src": "file3"}]),
            ]
        )
def test_loadHostDefaults(config, output):
    result = environ.loadHostDefaults(config)
    assert result == output

@pytest.mark.parametrize(("inputInventory", "outputInventory"),
            [
                # Verify null inputs
                ({}, {}),
                ({"all": {}}, {"all": {}}),
                ({"all": {"vars": {}}}, {"all": {"vars": {}}}),
                ({"all": {"vars": {"splunk": {}}}}, {"all": {"vars": {"splunk": {}}}}),
                # Verify individual keys to obfuscate
                ({"all": {"vars": {"splunk": {"password": "helloworld"}}}}, {"all": {"vars": {"splunk": {"password": "**************"}}}}),
                ({"all": {"vars": {"splunk": {"shc": {"secret": "helloworld"}}}}}, {"all": {"vars": {"splunk": {"shc": {"secret": "**************"}}}}}),
                ({"all": {"vars": {"splunk": {"smartstore": {"index": []}}}}}, {"all": {"vars": {"splunk": {"smartstore": {"index": []}}}}}),
                ({"all": {"vars": {"splunk": {"smartstore": {"index": [{"s3": {"access_key": "1234", "secret_key": "abcd"}}]}}}}}, {"all": {"vars": {"splunk": {"smartstore": {"index": [{"s3": {"access_key": "**************", "secret_key": "**************"}}]}}}}}),
            ]
        )
def test_obfuscate_vars(inputInventory, outputInventory):
    result = environ.obfuscate_vars(inputInventory)
    assert result == outputInventory

@pytest.mark.skip(reason="TODO")
def test_create_parser():
    pass

@pytest.mark.skip(reason="TODO")
def test_prep_for_yaml_out():
    pass

@pytest.mark.skip(reason="TODO")
def test_main():
    pass
