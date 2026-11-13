from pathlib import Path

import pytest
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar


# ---------------------------------------------------------------------------
# Pre-start indexer cluster configuration (CSPL-4136)
#
# Eligibility tests evaluate the role's actual YAML and Ansible expressions,
# including the facts that control the post-start fallback. The remaining helpers
# cover the existing replication-port, URI and configuration checks offline.
# ---------------------------------------------------------------------------

ROLE_TASKS = Path(__file__).resolve().parents[2] / 'roles'


def _task(loader, role, filename, name):
    tasks = loader.load_from_file(str(ROLE_TASKS / role / 'tasks' / filename))
    return next(task for task in tasks if task.get('name') == name)


def _prestart_facts(splunk, **initial_facts):
    """Evaluate the real set_fact tasks before the configuration-writing block."""
    loader = DataLoader()
    variables = dict(splunk_status={'rc': 3}, splunk=splunk)
    variables.update(initial_facts)
    for name in (
        'Resolve cluster manager host for pre-start clustering',
        'Determine whether pre-start clustering can be applied',
    ):
        task = _task(loader, 'splunk_common',
                     'configure_indexer_cluster_prestart.yml', name)
        templar = Templar(loader=loader, variables=variables)
        facts = {key: templar.template(value)
                 for key, value in task['set_fact'].items()}
        variables.update(facts)
    return variables


def _condition(role, filename, name, variables):
    loader = DataLoader()
    task = _task(loader, role, filename, name)
    conditional = Conditional(loader=loader)
    conditional.when = (task['when'] if isinstance(task['when'], list)
                        else [task['when']])
    return conditional.evaluate_conditional(
        Templar(loader=loader, variables=variables), variables)


def prestart_ssl_replication(splunk, splunk_conf_effective=None):
    '''
    Mirror idxc_prestart_ssl_replication.

    SSL peers already have [replication_port-ssl://PORT] from
    splunk.conf.server.content, so the bare [replication_port://PORT] stanza
    must only be written for non-SSL peers. Both mapping and list forms of
    splunk.conf are supported; the list form uses splunk_conf_effective
    (normalized at the Noah role boundary) to resolve entries.
    '''
    if (splunk.get('idxc') or {}).get('replication_ssl'):
        return True
    conf = splunk.get('conf')
    if isinstance(conf, dict):
        server = conf.get('server')
        if not isinstance(server, dict):
            return False
        content = server.get('content') or {}
    elif isinstance(conf, list):
        effective = splunk_conf_effective if splunk_conf_effective is not None else conf
        content = {}
        for entry in effective:
            if isinstance(entry, dict) and entry.get('key') == 'server':
                content = (entry.get('value') or {}).get('content') or {}
                break
    else:
        return False
    return any(str(k).startswith('replication_port-ssl://') for k in content)


def prestart_manager_uri(splunk):
    '''
    Mirror idxc_prestart_manager_uri.

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
    ({'cluster_master_url': 'cm', 'site': '', 'idxc': {'pass4SymmKey': 'k'}}, True),
    ({'cluster_master_url': 'cm', 'site': None, 'idxc': {'pass4SymmKey': 'k'}}, True),
    ({'cluster_master_url': 'cm', 'site': 'site1', 'idxc': {'pass4SymmKey': 'k'}}, False),
    ({'cluster_master_url': 'cm', 'site': 'site2', 'idxc': {'pass4SymmKey': 'k'}}, False),
    ({'cluster_master_url': 'cm', 'multisite_master': '',
      'site': 'site1', 'idxc': {'pass4SymmKey': 'k'}}, False),
    ({'cluster_master_url': 'cm', 'multisite_master': None,
      'site': 'site1', 'idxc': {'pass4SymmKey': 'k'}}, False),
    # A ready multisite peer need not know the complete all_sites list.
    ({'multisite_master': 'multisite-cm', 'site': 'site1',
      'idxc': {'pass4SymmKey': 'k'}}, True),
    ({'cluster_master_url': 'bootstrap-cm', 'multisite_master': 'multisite-cm',
      'site': 'site2', 'idxc': {'pass4SymmKey': 'k'}}, True),
    ({'cluster_master_url': '', 'idxc': {'pass4SymmKey': 'k'}}, False),
    ({'cluster_master_url': None, 'idxc': {'pass4SymmKey': 'k'}}, False),
    ({'cluster_master_url': 'cm', 'idxc': {'pass4SymmKey': ''}}, False),
    ({'cluster_master_url': 'cm', 'idxc': {}}, False),
    ({'cluster_master_url': 'cm'}, False),
])
def test_prestart_inputs_ok(splunk, expected):
    variables = _prestart_facts(splunk)
    assert variables['idxc_prestart_inputs_ok'] is expected
    assert _condition('splunk_common', 'configure_indexer_cluster_prestart.yml',
                      'Apply pre-start indexer cluster configuration', variables) is expected


@pytest.mark.parametrize('splunk', [
    {'cluster_master_url': 'cm', 'site': 'site1', 'idxc': {'pass4SymmKey': 'k'}},
    {'cluster_master_url': '', 'idxc': {'pass4SymmKey': 'k'}},
    {'cluster_master_url': 'cm', 'idxc': {'pass4SymmKey': ''}},
])
def test_skipped_prestart_clears_stale_fact_and_enables_post_start_fallback(splunk):
    variables = _prestart_facts(splunk, idxc_cluster_preseeded=True)
    assert variables['idxc_prestart_inputs_ok'] is False
    assert variables['idxc_cluster_preseeded'] is False
    assert _condition('splunk_indexer', 'indexer_clustering.yml',
                      'Set current node as indexer cluster peer', variables) is True
    assert _condition('splunk_indexer', 'setup_multisite.yml',
                      'Setup Peers with Associated Site', variables) is True


@pytest.mark.parametrize('splunk', [
    {'cluster_master_url': 'cm', 'idxc': {'pass4SymmKey': 'k'}},
    {'multisite_master': 'multisite-cm', 'site': 'site1',
     'idxc': {'pass4SymmKey': 'k'}},
    {'cluster_master_url': 'bootstrap-cm', 'multisite_master': 'multisite-cm',
     'site': 'site2', 'idxc': {'pass4SymmKey': 'k'}},
])
def test_running_indexer_uses_post_start_fallback_in_later_play(splunk):
    # Orca's later multisite play invokes the common role after splunkd has
    # already started. A stale success fact must not suppress its site join.
    variables = _prestart_facts(
        splunk, first_run=False, splunk_status={'rc': 0},
        idxc_cluster_preseeded=True)
    assert variables['idxc_prestart_inputs_ok'] is False
    assert variables['idxc_cluster_preseeded'] is False
    assert _condition('splunk_common', 'configure_indexer_cluster_prestart.yml',
                      'Apply pre-start indexer cluster configuration', variables) is False
    assert _condition('splunk_indexer', 'indexer_clustering.yml',
                      'Set current node as indexer cluster peer', variables) is True
    assert _condition('splunk_indexer', 'setup_multisite.yml',
                      'Setup Peers with Associated Site', variables) is True


@pytest.mark.parametrize('splunk', [
    {'cluster_master_url': 'cm', 'idxc': {'pass4SymmKey': 'k'}},
    {'multisite_master': 'multisite-cm', 'site': 'site1',
     'idxc': {'pass4SymmKey': 'k'}},
])
def test_stopped_initialized_indexer_can_still_preseed(splunk):
    # Existing installations can safely load the configuration on their next
    # start; first_run alone must not decide whether pre-seeding is allowed.
    variables = _prestart_facts(
        splunk, first_run=False, splunk_status={'rc': 3})
    assert variables['idxc_prestart_inputs_ok'] is True
    assert _condition('splunk_common', 'configure_indexer_cluster_prestart.yml',
                      'Apply pre-start indexer cluster configuration', variables) is True


def test_prestart_refreshes_process_status_before_deciding_or_writing():
    loader = DataLoader()
    tasks = loader.load_from_file(str(
        ROLE_TASKS / 'splunk_common' / 'tasks' / 'configure_indexer_cluster_prestart.yml'))
    names = [task.get('name') for task in tasks]
    status_name = 'Check indexer process state before pre-start clustering'
    assert status_name in names
    status_index = names.index(status_name)
    eligibility_index = names.index('Determine whether pre-start clustering can be applied')
    writes_index = names.index('Apply pre-start indexer cluster configuration')
    assert status_index < eligibility_index < writes_index
    status_include = tasks[status_index]
    assert status_include['include_tasks'] == 'get_splunk_status.yml'
    assert 'when' not in status_include

    status_task = _task(loader, 'splunk_common', 'get_splunk_status.yml', 'Get Splunk status')
    assert status_task['register'] == 'splunk_status'
    assert status_task['command'].startswith('{{ splunk.exec }} status ')
    assert 'when' not in status_task


@pytest.mark.parametrize(('splunk', 'splunk_conf_effective', 'expected'), [
    ({'idxc': {'replication_ssl': True}}, None, True),
    ({'conf': {'server': {'content': {'replication_port-ssl://9887': {}}}}}, None, True),
    ({'conf': {'server': {'content': {'replication_port://9887': {}}}}}, None, False),
    ({'conf': {'server': {'content': {}}}}, None, False),
    # list-based ConfigMap form – SSL stanza present
    ({'conf': [{'key': 'server', 'value': {'content': {'replication_port-ssl://9887': {}}}}]}, None, True),
    # list-based ConfigMap form – no SSL stanza
    ({'conf': [{'key': 'server', 'value': {'content': {'replication_port://9887': {}}}}]}, None, False),
    # list-based ConfigMap form – bare entry without content
    ({'conf': [{'key': 'server'}]}, None, False),
    # list-based with splunk_conf_effective (normalized) taking precedence
    (
        {'conf': [{'key': 'server', 'value': {'content': {}}}]},
        [{'key': 'server', 'value': {'content': {'replication_port-ssl://9887': {}}}}],
        True,
    ),
    ({}, None, False),
])
def test_prestart_ssl_replication(splunk, splunk_conf_effective, expected):
    assert prestart_ssl_replication(splunk, splunk_conf_effective) is expected


@pytest.mark.parametrize(('splunk', 'expected'), [
    ({'cluster_master_url': 'cm', 'svc_port': 8089}, 'https://cm:8089'),
    ({'cluster_master_url': 'cm', 'svc_port': 8089, 'ssl': {'enable': True}}, 'https://cm:8089'),
    ({'cluster_master_url': 'cm', 'svc_port': 8089, 'ssl': {'enable': False}}, 'http://cm:8089'),
    ({'multisite_master': 'ms', 'svc_port': 8089}, 'https://ms:8089'),
])
def test_prestart_manager_uri(splunk, expected):
    assert prestart_manager_uri(splunk) == expected


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


def _live_peer_guard():
    return _task(DataLoader(), 'splunk_indexer', 'indexer_clustering.yml',
                 'Verify pre-seeded Windows peer is active')


def _live_peer_variables(response, **overrides):
    variables = dict(_live_peer_guard()['vars'])
    variables.update(idxc_cluster_preseeded=True, ansible_system='Win32NT',
                     uds_enabled=False, idxc_prestart_live_peer=response)
    variables.update(overrides)
    return variables


def _evaluate(expressions, variables):
    loader = DataLoader()
    conditional = Conditional(loader=loader)
    conditional.when = expressions if isinstance(expressions, list) else [expressions]
    return conditional.evaluate_conditional(
        Templar(loader=loader, variables=variables), variables)


def _live_peer_validation(variables):
    task = next(task for task in _live_peer_guard()['block']
                if task.get('name') == 'Validate live indexer peer response')
    return _evaluate(task['assert']['that'], variables)


@pytest.mark.parametrize('response_kind', ['registered', 'unregistered', 'disabled'])
def test_windows_live_peer_controls_the_existing_post_start_fallback(response_kind):
    variables = _live_peer_variables({})
    if response_kind == 'registered':
        response = {'status': 200, 'json': {'entry': [{'content': {'is_registered': True}}]}}
    else:
        message = variables['idxc_peer_{}_message'.format(
            'unregistered' if response_kind == 'unregistered' else 'disabled')]
        response = {'status': 503, 'json': {'messages': [{'type': 'ERROR', 'text': message}]}}
    variables['idxc_prestart_live_peer'] = response
    assert _live_peer_validation(variables) is True

    fallback = next(task for task in _live_peer_guard()['block']
                    if task.get('name') == 'Use post-start configuration when Windows peer is not active')
    if _evaluate(fallback['when'], variables):
        variables.update({key: Templar(loader=DataLoader(), variables=variables).template(value)
                          for key, value in fallback['set_fact'].items()})
    assert variables['idxc_cluster_preseeded'] is (response_kind != 'disabled')
    assert _condition('splunk_indexer', 'indexer_clustering.yml',
                      'Set current node as indexer cluster peer', variables) is (response_kind == 'disabled')


@pytest.mark.parametrize('response', [
    {'status': 503, 'json': {'messages': [{'type': 'ERROR', 'text': 'Unknown peer failure'}]}},
    {'status': 503, 'json': {'messages': [{'type': 'ERROR', 'text': 'The cluster peer is not running.'}]}},
    {'status': 200, 'content': '<html>Login</html>'},
])
def test_windows_live_peer_rejects_unknown_terminal_or_login_responses(response):
    assert _live_peer_validation(_live_peer_variables(response)) is False


@pytest.mark.parametrize(('system', 'uds_enabled', 'preseeded', 'expected'), [
    ('Win32NT', False, True, True),
    ('CYGWIN_NT-10.0', False, True, True),
    ('Linux', False, True, False),
    ('Win32NT', True, True, False),
    ('Win32NT', False, False, False),
])
def test_live_peer_probe_is_limited_to_preseeded_windows_tcp(system, uds_enabled,
                                                          preseeded, expected):
    variables = _live_peer_variables({}, ansible_system=system,
                                     uds_enabled=uds_enabled, idxc_cluster_preseeded=preseeded)
    assert _evaluate(_live_peer_guard()['when'], variables) is expected
