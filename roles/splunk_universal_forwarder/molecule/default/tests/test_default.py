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
