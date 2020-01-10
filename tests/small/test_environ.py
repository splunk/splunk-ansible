#!/usr/bin/env python
'''
Unit tests for inventory/environ.py
'''
from __future__ import absolute_import

import os
import sys
import pytest
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
def test_getDefaultVars(mock_overrideEnvironmentVars, mock_loadDefaultSplunkVariables):
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
                ({}, {}, {"label": None, "secret": None}),
                # Check default.yml parameters
                ({"idxc": {}}, {}, {"label": None, "secret": None}),
                ({"idxc": {"label": None}}, {}, {"label": None, "secret": None}),
                ({"idxc": {"label": "1234"}}, {}, {"label": "1234", "secret": None}),
                ({"idxc": {"secret": None}}, {}, {"label": None, "secret": None}),
                ({"idxc": {"secret": "1234"}}, {}, {"label": None, "secret": "1234"}),
                # Check environment variable parameters
                ({}, {"SPLUNK_IDXC_LABEL": ""}, {"label": "", "secret": None}),
                ({}, {"SPLUNK_IDXC_LABEL": "abcd"}, {"label": "abcd", "secret": None}),
                ({}, {"SPLUNK_IDXC_SECRET": ""}, {"label": None, "secret": ""}),
                ({}, {"SPLUNK_IDXC_SECRET": "abcd"}, {"label": None, "secret": "abcd"}),
                # Check the union combination of default.yml + environment variables and order of precedence when overwriting
                ({"idxc": {"label": "1234"}}, {"SPLUNK_IDXC_LABEL": "abcd"}, {"label": "abcd", "secret": None}),
                ({"idxc": {"secret": "abcd"}}, {"SPLUNK_IDXC_SECRET": "1234"}, {"label": None, "secret": "1234"}),
            ]
        )
def test_getIndexerClustering(default_yml, os_env, output):
    vars_scope = {"splunk": default_yml}
    with patch("os.environ", new=os_env):
        environ.getIndexerClustering(vars_scope)
    assert type(vars_scope["splunk"]["idxc"]) == dict
    assert vars_scope["splunk"]["idxc"] == output

@pytest.mark.parametrize(("default_yml", "os_env", "output"),
            [
                # Check null parameters
                ({}, {}, {"label": None, "secret": None}),
                # Check default.yml parameters
                ({"shc": {}}, {}, {"label": None, "secret": None}),
                ({"shc": {"label": None}}, {}, {"label": None, "secret": None}),
                ({"shc": {"label": "1234"}}, {}, {"label": "1234", "secret": None}),
                ({"shc": {"secret": None}}, {}, {"label": None, "secret": None}),
                ({"shc": {"secret": "1234"}}, {}, {"label": None, "secret": "1234"}),
                # Check environment variable parameters
                ({}, {"SPLUNK_SHC_LABEL": ""}, {"label": "", "secret": None}),
                ({}, {"SPLUNK_SHC_LABEL": "abcd"}, {"label": "abcd", "secret": None}),
                ({}, {"SPLUNK_SHC_SECRET": ""}, {"label": None, "secret": ""}),
                ({}, {"SPLUNK_SHC_SECRET": "abcd"}, {"label": None, "secret": "abcd"}),
                # Check the union combination of default.yml + environment variables and order of precedence when overwriting
                ({"shc": {"label": "1234"}}, {"SPLUNK_SHC_LABEL": "abcd"}, {"label": "abcd", "secret": None}),
                ({"shc": {"secret": "abcd"}}, {"SPLUNK_SHC_SECRET": "1234"}, {"label": None, "secret": "1234"}),
            ]
        )
def test_getSearchHeadClustering(default_yml, os_env, output):
    vars_scope = {"splunk": default_yml}
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

@pytest.mark.parametrize(("os_env", "license_master_included", "deployer_included", "indexer_cluster", "search_head_cluster", "search_head_cluster_url"),
                         [
                            ({}, False, False, False, False, None),
                            # Check individual environment variables
                            ({"SPLUNK_LICENSE_MASTER_URL": "something"}, True, False, False, False, None),
                            ({"SPLUNK_DEPLOYER_URL": "something"}, False, True, False, False, None),
                            ({"SPLUNK_CLUSTER_MASTER_URL": "something"}, False, False, True, False, None),
                            ({"SPLUNK_SEARCH_HEAD_CAPTAIN_URL": "something"}, False, False, False, True, "something"),
                         ]
                        )
def test_getDistributedTopology(os_env, license_master_included, deployer_included, indexer_cluster, search_head_cluster, search_head_cluster_url):
    vars_scope = {"splunk": {}}
    with patch("os.environ", new=os_env):
        environ.getDistributedTopology(vars_scope)
    assert type(vars_scope["splunk"]["license_master_included"]) == bool
    assert vars_scope["splunk"]["license_master_included"] == license_master_included
    assert type(vars_scope["splunk"]["deployer_included"]) == bool
    assert vars_scope["splunk"]["deployer_included"] == deployer_included
    assert type(vars_scope["splunk"]["indexer_cluster"]) == bool
    assert vars_scope["splunk"]["indexer_cluster"] == indexer_cluster
    assert type(vars_scope["splunk"]["search_head_cluster"]) == bool
    assert vars_scope["splunk"]["search_head_cluster"] == search_head_cluster
    assert vars_scope["splunk"]["search_head_cluster_url"] == search_head_cluster_url

@pytest.mark.parametrize(("os_env", "license_uri", "wildcard_license", "nfr_license", "ignore_license", "license_download_dest"),
                         [
                            ({}, "splunk.lic", False, "/tmp/nfr_enterprise.lic", False, "/tmp/splunk.lic"),
                            # Check individual environment variables
                            ({"SPLUNK_LICENSE_URI": "http://web/license.lic"}, "http://web/license.lic", False, "/tmp/nfr_enterprise.lic", False, "/tmp/splunk.lic"),
                            ({"SPLUNK_LICENSE_URI": "/mnt/*.lic"}, "/mnt/*.lic", True, "/tmp/nfr_enterprise.lic", False, "/tmp/splunk.lic"),
                            ({"SPLUNK_NFR_LICENSE": "/mnt/nfr.lic"}, "splunk.lic", False, "/mnt/nfr.lic", False, "/tmp/splunk.lic"),
                            ({"SPLUNK_IGNORE_LICENSE": ""}, "splunk.lic", False, "/tmp/nfr_enterprise.lic", False, "/tmp/splunk.lic"),
                            ({"SPLUNK_IGNORE_LICENSE": "true"}, "splunk.lic", False, "/tmp/nfr_enterprise.lic", True, "/tmp/splunk.lic"),
                            ({"SPLUNK_IGNORE_LICENSE": "TRUE"}, "splunk.lic", False, "/tmp/nfr_enterprise.lic", True, "/tmp/splunk.lic"),
                            ({"SPLUNK_IGNORE_LICENSE": "false"}, "splunk.lic", False, "/tmp/nfr_enterprise.lic", False, "/tmp/splunk.lic"),
                            ({"SPLUNK_LICENSE_INSTALL_PATH": "/Downloads/"}, "splunk.lic", False, "/tmp/nfr_enterprise.lic", False, "/Downloads/"),
                         ]
                        )
def test_getLicenses(os_env, license_uri, wildcard_license, nfr_license, ignore_license, license_download_dest):
    vars_scope = {"splunk": {}}
    with patch("os.environ", new=os_env):
        environ.getLicenses(vars_scope)
    assert vars_scope["splunk"]["license_uri"] == license_uri
    assert type(vars_scope["splunk"]["wildcard_license"]) == bool
    assert vars_scope["splunk"]["wildcard_license"] == wildcard_license
    assert vars_scope["splunk"]["nfr_license"] == nfr_license
    assert type(vars_scope["splunk"]["ignore_license"]) == bool
    assert vars_scope["splunk"]["ignore_license"] == ignore_license
    assert vars_scope["splunk"]["license_download_dest"] == license_download_dest

@pytest.mark.parametrize(("os_env", "java_version", "java_download_url", "java_update_version"),
                         [
                            ({}, None, None, None),
                            # Check environment variable parameters
                            ({"JAVA": "oracle:8"}, None, None, None),
                            ({"JAVA_VERSION": "openjdk:8"}, "openjdk:8", None, None),
                            ({"JAVA_VERSION": "openjdk:9"}, "openjdk:9", None, None),
                            ({"JAVA_VERSION": "oracle:8"}, "oracle:8", "https://download.oracle.com/otn-pub/java/jdk/8u141-b15/336fa29ff2bb4ef291e347e091f7f4a7/jdk-8u141-linux-x64.tar.gz", "141"),
                            ({"JAVA_VERSION": "ORACLE:8"}, "oracle:8", "https://download.oracle.com/otn-pub/java/jdk/8u141-b15/336fa29ff2bb4ef291e347e091f7f4a7/jdk-8u141-linux-x64.tar.gz", "141"),
                            ({"JAVA_VERSION": "openjdk:11"}, "openjdk:11", "https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_linux-x64_bin.tar.gz", "11.0.2"),
                            ({"JAVA_VERSION": "oPenJdK:11"}, "openjdk:11", "https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_linux-x64_bin.tar.gz", "11.0.2"),
                            ({"JAVA_VERSION": "oracle:8", "JAVA_DOWNLOAD_URL": "https://java/jdk-8u9000-linux-x64.tar.gz"}, "oracle:8", "https://java/jdk-8u9000-linux-x64.tar.gz", "9000"),
                            ({"JAVA_VERSION": "openjdk:11", "JAVA_DOWNLOAD_URL": "https://java/openjdk-11.11.11_linux-x64_bin.tar.gz"}, "openjdk:11", "https://java/openjdk-11.11.11_linux-x64_bin.tar.gz", "11.11.11"),
                         ]
                        )
def test_getJava(os_env, java_version, java_download_url, java_update_version):
    vars_scope = {"splunk": {}}
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

@pytest.mark.parametrize(("default_yml", "os_env", "remote_src", "build"),
                         [
                            ({}, {}, False, None),
                            # Check default.yml parameters
                            ({"buildlocation": "http://server/file.tgz"}, {}, False, None),
                            ({"build_location": None}, {}, False, None),
                            ({"build_location": ""}, {}, False, ""),
                            ({"build_location": "/path/to/file.tgz"}, {}, False, "/path/to/file.tgz"),
                            ({"build_location": "http://server/file.tgz"}, {}, True, "http://server/file.tgz"),
                            ({"build_location": "https://server/file.tgz"}, {}, True, "https://server/file.tgz"),
                            # Check environment variable parameters
                            ({}, {"SPLUNK_BUILD": "http://server/file.tgz"}, False, None),
                            ({}, {"SPLUNK_BUILD_URL": None}, False, None),
                            ({}, {"SPLUNK_BUILD_URL": ""}, False, ""),
                            ({}, {"SPLUNK_BUILD_URL": "/path/to/file.tgz"}, False, "/path/to/file.tgz"),
                            ({}, {"SPLUNK_BUILD_URL": "http://server/file.tgz"}, True, "http://server/file.tgz"),
                            ({}, {"SPLUNK_BUILD_URL": "https://server/file.tgz"}, True, "https://server/file.tgz"),
                            # Check order of precedence
                            ({"build_location": "http://server/file1.tgz"}, {"SPLUNK_BUILD_URL": "https://server/file2.tgz"}, True, "https://server/file2.tgz"),
                            ({"build_location": "http://server/file1.tgz"}, {"SPLUNK_BUILD_URL": "/path/to/file.tgz"}, False, "/path/to/file.tgz"),
                         ]
                        )
def test_getSplunkBuild(default_yml, os_env, remote_src, build):
    vars_scope = dict()
    vars_scope["splunk"] = default_yml
    with patch("os.environ", new=os_env):
        environ.getSplunkBuild(vars_scope)
    assert type(vars_scope["splunk"]["build_remote_src"]) == bool
    assert vars_scope["splunk"]["build_remote_src"] == remote_src
    assert vars_scope["splunk"]["build_location"] == build

@pytest.mark.parametrize(("default_yml", "trigger_splunkbase"),
                         [
                            ({}, False),
                            ({"splunkbase_username": "ocho"}, False),
                            ({"splunkbase_password": "cinco"}, False),
                            ({"splunkbase_username": "ocho", "splunkbase_password": "cinco"}, True),
                            ({"splunkbase_username": "", "splunkbase_password": ""}, False),
                         ]
                        )
def test_getSplunkbaseToken(default_yml, trigger_splunkbase):
    vars_scope = default_yml
    with patch("environ.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, content="<id>123abc</id>")
        with patch("os.environ", new=dict()):
            environ.getSplunkbaseToken(vars_scope)
        # Make sure Splunkbase token is populated when appropriate
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

@pytest.mark.skip(reason="TODO")
def test_overrideEnvironmentVars():
    pass

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

@pytest.mark.parametrize(("os_env", "deployment_server", "add", "before_start_cmd", "cmd"),
                         [
                            ({}, None, None, None, None),
                            # Check environment variable parameters
                            ({"SPLUNK_DEPLOYMENT_SERVER": ""}, None, None, None, None),
                            ({"SPLUNK_DEPLOYMENT_SERVER": "something"}, "something", None, None, None),
                            ({"SPLUNK_ADD": ""}, None, None, None, None),
                            ({"SPLUNK_ADD": "echo 1"}, None, ["echo 1"], None, None),
                            ({"SPLUNK_ADD": "echo 1,echo 2"}, None, ["echo 1", "echo 2"], None, None),
                            ({"SPLUNK_BEFORE_START_CMD": ""}, None, None, None, None),
                            ({"SPLUNK_BEFORE_START_CMD": "echo 1"}, None, None, ["echo 1"], None),
                            ({"SPLUNK_BEFORE_START_CMD": "echo 1,echo 2"}, None, None, ["echo 1", "echo 2"], None),
                            ({"SPLUNK_CMD": ""}, None, None, None, None),
                            ({"SPLUNK_CMD": "echo 1"}, None, None, None, ["echo 1"]),
                            ({"SPLUNK_CMD": "echo 1,echo 2"}, None, None, None, ["echo 1", "echo 2"]),
                         ]
                        )
def test_getUFSplunkVariables(os_env, deployment_server, add, before_start_cmd, cmd):
    vars_scope = {"splunk": {}}
    with patch("os.environ", new=os_env):
        environ.getUFSplunkVariables(vars_scope)
    assert vars_scope["splunk"].get("deployment_server") == deployment_server
    assert vars_scope["splunk"].get("add") == add
    assert vars_scope["splunk"].get("before_start_cmd") == before_start_cmd
    assert vars_scope["splunk"].get("cmd") == cmd

def test_getRandomString():
    word = environ.getRandomString()
    assert len(word) == 6

@pytest.mark.skip(reason="TODO")
def test_merge_dict():
    pass

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

@pytest.mark.skip(reason="TODO")
def test_mergeDefaultsFromURL():
    pass

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
