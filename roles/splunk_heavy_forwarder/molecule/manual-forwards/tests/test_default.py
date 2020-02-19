#!/usr/bin/env python
from __future__ import absolute_import
import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_splunk_running(host):
    output = host.run('/opt/splunk/bin/splunk status')
    assert "running" in output.stdout


def test_user_seed(host):
    f = host.file('/opt/splunk/etc/system/local/user-seed.conf')
    assert not f.exists


def test_ui_login(host):
    f = host.file('/opt/splunk/etc/.ui_login')
    assert f.exists
    assert f.user == 'splunk'
    assert f.group == 'splunk'


def test_bin_splunk(host):
    f = host.file('/opt/splunk/bin/splunk')
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
    f = host.file('/opt/splunk/etc/users/admin/user-prefs/local/user-prefs.conf')
    assert f.exists
    assert f.user == 'splunk'
    assert f.group == 'splunk'
    assert f.contains("[general]")
    assert f.contains("default_namespace = appboilerplate")
    assert f.contains("search_syntax_highlighting = dark")


def test_splunkweb_root_endpoint(host):
    output = host.run('curl http://localhost:8080/splunkui/en-US/')
    assert "This resource can be found at" in output.stdout
    assert "/account/login?return_to" in output.stdout


def test_forward_servers(host):
    f = host.file('/opt/splunk/etc/system/local/outputs.conf')
    assert f.exists
    assert f.user == 'splunk'
    assert f.group == 'splunk'
    assert f.contains("\\[tcpout-server://forwarder1.test.com:9997\\]")
    assert f.contains("\\[tcpout-server://forwarder2.test.com:9997\\]")
    assert f.contains("\\[tcpout:default-autolb-group\\]")
    assert f.contains("server = forwarder1.test.com:9997,forwarder2.test.com:9997")
