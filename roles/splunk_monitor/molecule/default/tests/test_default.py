#!/usr/bin/env python
#
# These tests specifically exercise the following:
# - Multiple platform support (centos, debian, redhat)
# - Splunk version 8.0.3
# - Normal splunk_monitor with minimal option set

from __future__ import absolute_import
import os
import json

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

def test_ui_login(host):
    f = host.file("{}/etc/.ui_login".format(SPLUNK_HOME))
    assert f.exists
    assert f.user == SPLUNK_USER
    assert f.group == SPLUNK_GROUP

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

def test_splunk_ports(host):
    output = host.run("netstat -tuln")
    assert "0.0.0.0:8000" in output.stdout
    assert "0.0.0.0:8089" in output.stdout

def test_monitor(host):
    output = host.run("curl -k https://localhost:8089/servicesNS/nobody/splunk_monitoring_console/configs/conf-splunk_monitoring_console_assets/settings \
        -u admin:helloworld -d output_mode=json")
    output = json.loads(output.stdout)
    assert output["entry"][0]["content"]["disabled"] == False
