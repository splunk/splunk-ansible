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


def test_splunk_hec(host):
    output = host.run('curl -k https://localhost:8088/services/collector/event \
        -H "Authorization: Splunk abcd1234" -d \'{"event": "helloworld"}\'')
    assert "Success" in output.stdout


def test_splunkd(host):
    output = host.run('curl -k https://localhost:8089/services/server/info \
        -u admin:helloworld')
    assert "Splunk" in output.stdout


def test_custom_user_prefs(host):
    f = host.file('/opt/splunk/etc/users/admin/user-prefs/local/user-prefs.conf')
    assert f.exists
    assert f.user == splunk_user
    assert f.group == splunk_group
    assert f.contains("[general]")
    assert f.contains("default_namespace = appboilerplate")
    assert f.contains("search_syntax_highlighting = dark")


def test_splunkweb_root_endpoint(host):
    output = host.run('curl http://localhost:8080/splunkui/en-US/')
    assert "This resource can be found at" in output.stdout
    assert "/account/login?return_to" in output.stdout


def test_service(host):
    s = host.service('Splunkd')
    assert s.is_running
    assert s.is_enabled


def test_splunkd_systemd_file(host):
    f = host.file('/etc/systemd/system/Splunkd.service')
    assert f.is_file
    assert f.user == "root"
    assert f.group == "root"
    assert f.contains('ExecStartPost=/bin/bash -c "chown -R splunk:splunk /sys/fs/cgroup/cpu/system.slice/%n"')
    assert f.contains('ExecStartPost=/bin/bash -c "chown -R splunk:splunk /sys/fs/cgroup/memory/system.slice/%n"')
