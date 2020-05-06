#!/usr/bin/env python
from __future__ import absolute_import
import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')

splunk_home = '/opt/splunk'
splunk = "%s/bin/splunk" % splunk_home
splunk_user = 'splunk'
splunk_group = 'splunk'


def test_splunk_user_group(host):
    user = host.user(splunk_user)
    assert user.name == splunk_user
    assert user.group == splunk_group


def test_splunk_installation(host):
    dir = host.file(splunk_home)
    assert dir.is_directory
    assert dir.user == splunk_user
    assert dir.group == splunk_group

    f = host.file(splunk)
    assert f.is_file
    assert f.user == splunk_user
    assert f.group == splunk_group


def test_splunk_running(host):
    output = host.run('/opt/splunk/bin/splunk status')
    assert "running" in output.stdout


def test_user_seed(host):
    f = host.file('/opt/splunk/etc/system/local/user-seed.conf')
    assert not f.exists


def test_ui_login(host):
    f = host.file('/opt/splunk/etc/.ui_login')
    assert f.exists
    assert f.user == splunk_user
    assert f.group == splunk_group


def test_bin_splunk(host):
    f = host.file('/opt/splunk/bin/splunk')
    assert f.exists
    assert f.user == splunk_user
    assert f.group == splunk_group


def test_splunkd(host):
    output = host.run('curl -k https://localhost:8089/services/server/info \
        -u admin:helloworld')
    assert "Splunk" in output.stdout


def test_outputs(host):
    f = host.file('/opt/splunk/etc/system/local/outputs.conf')
    assert not f.exists
