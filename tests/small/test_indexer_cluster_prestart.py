import pytest


# ---------------------------------------------------------------------------
# Pre-start indexer cluster configuration (CSPL-4136)
#
# These mirror the Jinja expressions in
# roles/splunk_common/tasks/configure_indexer_cluster_prestart.yml so the guard
# logic is covered without standing up a cluster.
# ---------------------------------------------------------------------------

def prestart_inputs_ok(splunk):
    '''
    Mirror idxc_prestart_inputs_ok.

    Without a cluster manager address or a cluster secret there is nothing safe
    to write, so the pre-seed is skipped and the post-start
    `splunk edit cluster-config` fallback runs instead.
    '''
    cm_host = splunk.get('multisite_master') or splunk.get('cluster_master_url') or ''
    secret = (splunk.get('idxc') or {}).get('pass4SymmKey') or ''
    return bool(cm_host) and bool(secret)


def prestart_ssl_replication(splunk):
    '''
    Mirror idxc_prestart_ssl_replication.

    SSL peers already have [replication_port-ssl://PORT] from
    splunk.conf.server.content, so the bare [replication_port://PORT] stanza
    must only be written for non-SSL peers.
    '''
    if (splunk.get('idxc') or {}).get('replication_ssl'):
        return True
    conf = splunk.get('conf')
    if not isinstance(conf, dict):
        return False
    server = conf.get('server')
    if not isinstance(server, dict):
        return False
    content = server.get('content') or {}
    return any(str(k).startswith('replication_port-ssl://') for k in content)


def prestart_master_uri(splunk):
    '''
    Mirror idxc_prestart_master_uri.

    cert_prefix is only set after start_splunk, by probing the local splunkd.
    enable_splunkd_ssl.yml disables SSL only when splunk.ssl.enable is falsy, so
    splunkd serves https unless SSL was explicitly turned off. Deriving the
    scheme from config avoids a network probe that could pick the wrong one.
    '''
    ssl_enable = (splunk.get('ssl') or {}).get('enable', True)
    scheme = 'https' if ssl_enable else 'http'
    cm_host = splunk.get('multisite_master') or splunk.get('cluster_master_url')
    return '{}://{}:{}'.format(scheme, cm_host, splunk.get('svc_port', 8089))


def cluster_preseeded(server_conf, site=None):
    '''
    Mirror idxc_cluster_preseeded.

    The flag suppresses the post-start fallback, so it must only be set when
    server.conf verifiably contains everything the peer needs. A partially
    applied run must leave the fallback enabled.
    '''
    return (
        '[clustering]' in server_conf
        and 'master_uri = ' in server_conf
        and 'mode = peer' in server_conf
        and ('[replication_port-ssl://' in server_conf or '[replication_port://' in server_conf)
        and (not site or 'site = ' in server_conf)
    )


@pytest.mark.parametrize(('splunk', 'expected'), [
    ({'cluster_master_url': 'cm', 'idxc': {'pass4SymmKey': 'k'}}, True),
    ({'multisite_master': 'cm', 'idxc': {'pass4SymmKey': 'k'}}, True),
    ({'cluster_master_url': '', 'idxc': {'pass4SymmKey': 'k'}}, False),
    ({'cluster_master_url': 'cm', 'idxc': {'pass4SymmKey': ''}}, False),
    ({'cluster_master_url': 'cm', 'idxc': {}}, False),
    ({}, False),
])
def test_prestart_inputs_ok(splunk, expected):
    assert prestart_inputs_ok(splunk) is expected


@pytest.mark.parametrize(('splunk', 'expected'), [
    ({'idxc': {'replication_ssl': True}}, True),
    ({'conf': {'server': {'content': {'replication_port-ssl://9887': {}}}}}, True),
    ({'conf': {'server': {'content': {'replication_port://9887': {}}}}}, False),
    ({'conf': {'server': {'content': {}}}}, False),
    # list-based ConfigMap form must not raise
    ({'conf': [{'key': 'server'}]}, False),
    ({}, False),
])
def test_prestart_ssl_replication(splunk, expected):
    assert prestart_ssl_replication(splunk) is expected


@pytest.mark.parametrize(('splunk', 'expected'), [
    ({'cluster_master_url': 'cm', 'svc_port': 8089}, 'https://cm:8089'),
    ({'cluster_master_url': 'cm', 'svc_port': 8089, 'ssl': {'enable': True}}, 'https://cm:8089'),
    ({'cluster_master_url': 'cm', 'svc_port': 8089, 'ssl': {'enable': False}}, 'http://cm:8089'),
    ({'multisite_master': 'ms', 'svc_port': 8089}, 'https://ms:8089'),
])
def test_prestart_master_uri(splunk, expected):
    assert prestart_master_uri(splunk) == expected


SSL_CONF = (
    '[clustering]\nmaster_uri = https://cm:8089\nmode = peer\n'
    '[replication_port-ssl://9887]\n'
)
NON_SSL_CONF = (
    '[clustering]\nmaster_uri = https://cm:8089\nmode = peer\n'
    '[replication_port://9887]\n'
)


def test_cluster_preseeded_ssl_single_site():
    assert cluster_preseeded(SSL_CONF) is True


def test_cluster_preseeded_non_ssl_single_site():
    assert cluster_preseeded(NON_SSL_CONF) is True


def test_cluster_preseeded_requires_site_when_multisite():
    assert cluster_preseeded(SSL_CONF, site='site1') is False
    assert cluster_preseeded(SSL_CONF + 'site = site1\n', site='site1') is True


@pytest.mark.parametrize('server_conf', [
    # no replication port stanza: splunkd aborts with
    # 'clustering initialization failed err="need to specify replication port"'
    '[clustering]\nmaster_uri = https://cm:8089\nmode = peer\n',
    # no master_uri
    '[clustering]\nmode = peer\n[replication_port://9887]\n',
    # no mode
    '[clustering]\nmaster_uri = https://cm:8089\n[replication_port://9887]\n',
    # no clustering stanza at all
    '[replication_port://9887]\n',
])
def test_cluster_preseeded_false_on_partial_write(server_conf):
    assert cluster_preseeded(server_conf) is False
