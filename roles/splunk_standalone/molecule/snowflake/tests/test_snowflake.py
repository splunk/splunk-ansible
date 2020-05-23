#!/usr/bin/env python
#
# These tests specifically exercise more esoteric options of splunk-ansible, including:
# - Multiple platform support (debian, redhat)
# - Splunk version 7.3.5
# - Changing web, mgmt, HEC, splunktcp ports
# - Configuring splunk.secret
# - Adding key-value pairs to splunk-launch.conf
# - Enabling custom configuration user-prefs.conf
# - Changing root_endpoint for SplunkWeb

from __future__ import absolute_import
import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

SPLUNK_HOME = "/opt/splunk"
SPLUNK_EXEC = "{}/bin/splunk".format(SPLUNK_HOME)
SPLUNK_USER = SPLUNK_GROUP = "splunk"


def test_splunk_user_group(host):
    user = host.user(SPLUNK_USER)
    assert user.name == SPLUNK_USER
    assert user.group == SPLUNK_GROUP

def test_splunk_installation(host):
    d = host.file(SPLUNK_HOME)
    assert d.is_directory
    assert d.user == SPLUNK_USER
    assert d.group == SPLUNK_GROUP
    f = host.file(SPLUNK_EXEC)
    assert f.is_file
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP

def test_splunk_running(host):
    output = host.run("{} status".format(SPLUNK_EXEC))
    assert "running" in output.stdout

def test_user_seed(host):
    f = host.file("{}/etc/system/local/user-seed.conf".format(SPLUNK_HOME))
    assert not f.exists

def test_outputs_conf(host):
    f = host.file('/opt/splunk/etc/system/local/outputs.conf')
    assert not f.exists

def test_ui_login(host):
    f = host.file("{}/etc/.ui_login".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP

def test_splunk_version(host):
    f = host.file("{}/etc/splunk.version".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("VERSION=7.3.5")

def test_splunk_pid(host):
    f = host.file("{}/var/run/splunk/splunkd.pid".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP

def test_mongod_lock(host):
    f = host.file("{}/var/lib/splunk/kvstore/mongo/mongod.lock".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP

def test_bin_splunk(host):
    f = host.file("{}".format(SPLUNK_EXEC))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP

def test_splunk_hec_inputs(host):
    f = host.file("{}/etc/apps/splunk_httpinput/local/inputs.conf".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("[http]")
    assert f.contains("disabled = 0")
    assert f.contains("[http://splunk_hec_token]")
    assert f.contains("token = qwerty789")

def test_inputs_conf(host):
    f = host.file("{}/etc/system/local/inputs.conf".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("[splunktcp://9999]")
    assert f.contains("disabled = 0")

def test_splunk_ports(host):
    output = host.run("netstat -tuln")
    assert "0.0.0.0:8080" in output.stdout
    assert "0.0.0.0:8090" in output.stdout
    assert "0.0.0.0:8099" in output.stdout
    assert "0.0.0.0:18191" in output.stdout
    assert "0.0.0.0:9999" in output.stdout
    assert "127.0.0.1:8066" in output.stdout

def test_appserver_port(host):
    f = host.file("{}/etc/system/local/web.conf".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("[settings]")
    assert f.contains("appServerPorts = 8066")

def test_kvstore_port(host):
    f = host.file("{}/etc/system/local/server.conf".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("[kvstore]")
    assert f.contains("port = 18191")

def test_splunk_secret(host):
    f = host.file("{}/etc/auth/splunk.secret".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("pewpewpew")

def test_splunk_launch(host):
    f = host.file("{}/etc/splunk-launch.conf".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("OPTIMISTIC_ABOUT_FILE_LOCKING=1")
    assert f.contains("TEST=A=B")

def test_custom_user_prefs(host):
    f = host.file("{}/etc/users/admin/user-prefs/local/user-prefs.conf".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("[general]")
    assert f.contains("default_namespace = appboilerplate")
    assert f.contains("search_syntax_highlighting = dark")
    assert f.contains("search_assistant")
    assert f.contains("[serverClass:secrets:app:test]")

def test_splunk_hec(host):
    output = host.run('curl -k http://localhost:8099/services/collector/event \
        -H "Authorization: Splunk qwerty789" -d \'{"event": "helloworld"}\'')
    assert "Success" in output.stdout

def test_splunkd(host):
    output = host.run("curl -k https://localhost:8090/services/server/info \
        -u admin:helloworld2")
    assert "Splunk" in output.stdout

def test_web_conf(host):
    f = host.file("{}/etc/system/local/web.conf".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP
    assert f.contains("[settings]")
    assert f.contains("root_endpoint = /splunkui")

def test_splunkweb_root_endpoint(host):
    output = host.run('curl http://localhost:8080/splunkui/en-US/')
    assert "This resource can be found at" in output.stdout
    assert "/account/login?return_to" in output.stdout
