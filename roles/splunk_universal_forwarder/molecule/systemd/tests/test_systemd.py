#!/usr/bin/env python
from __future__ import absolute_import
import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_splunk_running(host):
    output = host.run('/opt/splunkforwarder/bin/splunk status')
    assert "running" in output.stdout


def test_user_seed(host):
    f = host.file('/opt/splunkforwarder/etc/system/local/user-seed.conf')
    assert not f.exists


def test_ui_login(host):
    f = host.file('/opt/splunkforwarder/etc/.ui_login')
    assert f.exists
    assert f.user == 'splunk'
    assert f.group == 'splunk'


def test_bin_splunk(host):
    f = host.file('/opt/splunkforwarder/bin/splunk')
    assert f.exists
    assert f.user == 'splunk'
    assert f.group == 'splunk'


def test_splunk_hec(host):
    output = host.run('curl -k https://localhost:8088/services/collector/event \
        -H "Authorization: Splunk abcd1234" -d \'{"event": "helloworld"}\'')
    assert "Success" in output.stdout


def test_splunkd(host):
    output = host.run('curl -k https://localhost:8089/services/server/info \
        -u admin:helloworld')
    assert "Splunk" in output.stdout


def test_custom_user_prefs(host):
    f = host.file('/opt/splunkforwarder/etc/users/admin/user-prefs/local/user-prefs.conf')
    assert f.exists
    assert f.user == 'splunk'
    assert f.group == 'splunk'
    assert f.contains("[general]")
    assert f.contains("default_namespace = appboilerplate")
    assert f.contains("search_syntax_highlighting = dark")


def test_service(host):
    s = host.service('SplunkForwarder')
    assert s.is_running
    assert s.is_enabled


def test_splunkforwarder_systemd_file(host):
    # This test uses Splunk UF version 8.0.2, which now does not have ExecStartPost directives
    f = host.file('/etc/systemd/system/SplunkForwarder.service')
    assert f.is_file
    assert f.user == "root"
    assert f.group == "root"
    assert "ExecStartPost" not in f.content_string
