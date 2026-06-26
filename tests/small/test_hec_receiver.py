#!/usr/bin/env python
'''
Unit tests for roles/splunk_common/tasks/set_as_hec_receiver.yml logic.

These tests mirror the Jinja2 expressions in the task file in pure Python so
that the guard conditions and hec_global_body construction can be validated
without running a live Ansible playbook.  Any change to the task's `when`
clause or the `set_fact` expression should be reflected here.
'''
from __future__ import absolute_import

import pytest


# ---------------------------------------------------------------------------
# Python equivalents of the Ansible Jinja2 expressions
# ---------------------------------------------------------------------------

def _bool(v):
    '''Mimic Ansible's | bool filter: truthy strings and booleans -> True.'''
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ('1', 'true', 'yes', 'on')
    return bool(v)


def should_build_hec_body(splunk):
    '''
    Mirror the `when` guard on "Build global HEC body".

    Returns True when the task should run (i.e. hec_global_body is defined).
    Must stay in sync with set_as_hec_receiver.yml.
    '''
    hec = splunk.get('hec', {})
    if 'hec' in splunk and (
        'enable' in hec or 'ssl' in hec or 'port' in hec
        or 'cert' in hec or 'password' in hec
    ):
        return True
    if 'hec_disabled' in splunk:
        return True
    if 'hec_enableSSL' in splunk:
        return True
    if 'hec_port' in splunk:
        return True
    return False


def build_hec_global_body(splunk):
    '''
    Mirror the `set_fact: hec_global_body` Jinja2 expression.

    Returns the dict that would be POSTed to the Splunk REST API, or None
    when the guard does not fire.  Must stay in sync with
    set_as_hec_receiver.yml.
    '''
    if not should_build_hec_body(splunk):
        return None

    hec = splunk.get('hec', {})

    # disabled
    if ('hec' in splunk and 'enable' in hec and _bool(hec['enable'])) or \
       ('hec_disabled' in splunk and not _bool(splunk['hec_disabled'])):
        disabled = '0'
    else:
        disabled = '1'

    # port
    if 'hec' in splunk and 'port' in hec and hec['port']:
        port = hec['port']
    elif 'hec_port' in splunk and splunk['hec_port']:
        port = splunk['hec_port']
    else:
        port = '8088'

    # serverCert
    server_cert = hec['cert'] if ('hec' in splunk and 'cert' in hec and hec['cert']) else ''

    # sslPassword
    ssl_password = hec['password'] if ('hec' in splunk and 'password' in hec and hec['password']) else ''

    body = {
        'disabled': disabled,
        'port': port,
        'serverCert': server_cert,
        'sslPassword': ssl_password,
    }

    # enableSSL — splunk.hec.ssl takes precedence over deprecated hec_enableSSL
    if 'hec' in splunk and 'ssl' in hec and hec['ssl'] is not None:
        body['enableSSL'] = '1' if _bool(hec['ssl']) else '0'
    elif 'hec_enableSSL' in splunk:
        body['enableSSL'] = '1' if _bool(splunk['hec_enableSSL']) else '0'

    return body


# ---------------------------------------------------------------------------
# Guard / `when` condition tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(('splunk', 'expected'), [
    # Guard must NOT fire — no HEC fields at all (custom httpinput preserved)
    ({}, False),
    ({'hec': {}}, False),
    ({'hec': {'token': 'abc'}}, False),   # token-only, no global fields

    # Guard MUST fire — splunk.hec.* fields
    ({'hec': {'enable': True}}, True),
    ({'hec': {'ssl': True}}, True),
    ({'hec': {'ssl': False}}, True),
    ({'hec': {'port': 9088}}, True),
    ({'hec': {'cert': '/path/cert.pem'}}, True),
    # Password-only: guard must fire (this was the bug being fixed)
    ({'hec': {'password': 's3cr3t'}}, True),

    # Guard MUST fire — deprecated hec_* top-level vars
    ({'hec_disabled': True}, True),
    ({'hec_disabled': False}, True),
    ({'hec_enableSSL': True}, True),
    ({'hec_enableSSL': False}, True),   # explicit false must fire too
    ({'hec_port': 8888}, True),
])
def test_should_build_hec_body(splunk, expected):
    assert should_build_hec_body(splunk) == expected


# ---------------------------------------------------------------------------
# hec_global_body construction tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(('splunk', 'expected_body'), [
    # Guard does not fire — body is None (custom httpinput preserved)
    ({}, None),
    ({'hec': {}}, None),
    ({'hec': {'token': 'only-token'}}, None),

    # --- enableSSL via splunk.hec.ssl ---
    (
        {'hec': {'ssl': True}},
        {'disabled': '1', 'port': '8088', 'serverCert': '', 'sslPassword': '', 'enableSSL': '1'},
    ),
    (
        {'hec': {'ssl': False}},
        {'disabled': '1', 'port': '8088', 'serverCert': '', 'sslPassword': '', 'enableSSL': '0'},
    ),

    # --- enableSSL via deprecated hec_enableSSL ---
    # True produces '1'
    (
        {'hec_enableSSL': True},
        {'disabled': '1', 'port': '8088', 'serverCert': '', 'sslPassword': '', 'enableSSL': '1'},
    ),
    # False must produce '0', NOT be silently dropped (regression guard)
    (
        {'hec_enableSSL': False},
        {'disabled': '1', 'port': '8088', 'serverCert': '', 'sslPassword': '', 'enableSSL': '0'},
    ),

    # splunk.hec.ssl takes precedence over hec_enableSSL
    (
        {'hec': {'ssl': False}, 'hec_enableSSL': True},
        {'disabled': '1', 'port': '8088', 'serverCert': '', 'sslPassword': '', 'enableSSL': '0'},
    ),

    # --- password-only guard fix ---
    (
        {'hec': {'password': 'mypassword'}},
        {'disabled': '1', 'port': '8088', 'serverCert': '', 'sslPassword': 'mypassword'},
    ),

    # --- cert + password together ---
    (
        {'hec': {'cert': '/mnt/cert.pem', 'password': 'p@ssw0rd', 'ssl': True}},
        {'disabled': '1', 'port': '8088', 'serverCert': '/mnt/cert.pem', 'sslPassword': 'p@ssw0rd', 'enableSSL': '1'},
    ),

    # --- port override ---
    (
        {'hec': {'port': 9088, 'ssl': True}},
        {'disabled': '1', 'port': 9088, 'serverCert': '', 'sslPassword': '', 'enableSSL': '1'},
    ),
    (
        {'hec_port': 7777},
        {'disabled': '1', 'port': 7777, 'serverCert': '', 'sslPassword': ''},
    ),

    # --- enable / disabled ---
    (
        {'hec': {'enable': True}},
        {'disabled': '0', 'port': '8088', 'serverCert': '', 'sslPassword': ''},
    ),
    (
        {'hec_disabled': False},
        {'disabled': '0', 'port': '8088', 'serverCert': '', 'sslPassword': ''},
    ),
    (
        {'hec_disabled': True},
        {'disabled': '1', 'port': '8088', 'serverCert': '', 'sslPassword': ''},
    ),
])
def test_build_hec_global_body(splunk, expected_body):
    result = build_hec_global_body(splunk)
    assert result == expected_body


# ---------------------------------------------------------------------------
# Stale config-file removal guard
# ---------------------------------------------------------------------------

def should_remove_conf_file(conf_directory, conf_stanzas):
    '''
    Mirror the `when` guard on "Remove stale <conf_file> before writing
    config map values" in set_config_file.yml.

    The task removes the file only when conf_directory is defined AND
    conf_stanzas is non-empty.
    '''
    return conf_directory is not None and len(conf_stanzas) > 0


@pytest.mark.parametrize(('conf_directory', 'conf_stanzas', 'expected'), [
    # conf_directory undefined — never remove
    (None, {}, False),
    (None, {'stanza1': {'key': 'val'}}, False),

    # conf_directory defined but no stanzas — skip removal (nothing to write)
    ('/opt/splunk/etc/system/local', {}, False),

    # conf_directory defined and stanzas present — remove stale file
    ('/opt/splunk/etc/system/local', {'stanza1': {'key': 'val'}}, True),
    ('/opt/splunk/etc/system/local', {'a': {}, 'b': {}}, True),
])
def test_should_remove_conf_file(conf_directory, conf_stanzas, expected):
    assert should_remove_conf_file(conf_directory, conf_stanzas) == expected
