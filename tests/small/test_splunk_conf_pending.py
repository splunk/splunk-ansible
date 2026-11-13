#!/usr/bin/env python
"""Unit tests for the splunk_conf_pending module and filters in roles/splunk_common (CSPL-5741)."""

from __future__ import absolute_import

import importlib.util
import os

import pytest

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
ROLE_DIR = os.path.join(FILE_DIR, "..", "..", "roles", "splunk_common")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


module = load("splunk_conf_pending_module", os.path.join(ROLE_DIR, "library", "splunk_conf_pending.py"))
filters = load("splunk_conf_pending_filters", os.path.join(ROLE_DIR, "filter_plugins", "splunk_conf_pending.py"))

DO_INI, DO_INI_REASON = module.load_do_ini()
needs_do_ini = pytest.mark.skipif(DO_INI is None, reason="supported community.general not installed")


def write(tmp_path, content, name="server.conf"):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def test_parse_version():
    assert module.parse_version("10.7.6") == (10, 7, 6)
    assert module.parse_version("11.0.0-a1") == (11, 0, 0)
    assert module.parse_version("12") == (12, 0, 0)


def test_unsupported_community_general_version_is_reported(monkeypatch):
    monkeypatch.setattr(module, "SUPPORTED_COMMUNITY_GENERAL", ((1, 0, 0), (2, 0, 0)))
    do_ini, reason = module.load_do_ini()
    assert do_ini is None
    assert "outside the supported range" in reason or "cannot import" in reason


@needs_do_ini
def test_matching_options_are_not_pending(tmp_path):
    path = write(tmp_path, "[general]\nserverName = idx-1\nsite = site1\n")
    pending, reason, options = module.inspect_file(
        DO_INI, path, {"general": {"serverName": "idx-1", "site": "site1"}})
    assert (pending, reason, options) == ([], None, 2)


@needs_do_ini
def test_only_differing_options_are_pending(tmp_path):
    path = write(tmp_path, "[general]\nserverName = idx-1\n# site = site1\n[sslConfig]\nsslVersions = tls1.2\n")
    pending, reason, _ = module.inspect_file(DO_INI, path, {
        "general": {"serverName": "idx-1", "site": "site1", "new": "x"},
        "sslConfig": {"sslVersions": "tls1.2"},
        "missing": {"a": "1"},
    })
    assert reason is None
    assert pending == [["general", ["site", "new"]], ["missing", ["a"]]]


@needs_do_ini
def test_values_are_compared_as_ini_file_strings(tmp_path):
    path = write(tmp_path, "[s]\ni = 500\nb = True\nf = 1.5\ne = \n")
    pending, _, _ = module.inspect_file(DO_INI, path, {"s": {"i": 500, "b": True, "f": 1.5, "e": ""}})
    assert pending == []


@needs_do_ini
@pytest.mark.parametrize("stanzas", [
    {" padded ": {"x": "1"}},
    {"s]x": {"x": "1"}},
    {"s": {"multi": "x\ny"}},
    {"s": {"json": '{"hello":"world"}'}},
    {"s": {"list": "[1,2]"}},
    {"s": {"jinja": "a{{ b }}"}},
    {"s": {'{"x":1}': "1"}},
    {'{"x":1}': {"a": "1"}},
    {"s": {"none": None}},
    {"s": {"list": ["a"]}},
    {"s": {" a": "1"}},
    {"s": {"a=b": "1"}},
    {"s": {"#a": "1"}},
    {"s": {";a": "1"}},
    {"s": {"[a": "1"}},
    {"s": "not a mapping"},
], ids=["padded_stanza", "bracket_in_stanza", "multiline_value", "json_string", "list_string", "jinja_string", "json_option_name",
        "json_stanza_name", "none_value", "list_value", "padded_option",
        "equals_in_option", "hash_option", "semicolon_option", "bracket_option", "non_mapping"])
def test_unusual_names_and_values_make_the_file_unsupported(tmp_path, stanzas):
    path = write(tmp_path, "[s]\na = 1\n")
    pending, reason, _ = module.inspect_file(DO_INI, path, dict(stanzas, ok={"a": "1"}))
    assert pending is None and reason.startswith("unsupported")


@needs_do_ini
def test_empty_stanzas_are_not_reported(tmp_path):
    path = write(tmp_path, "[s]\na = 1\n")
    assert module.inspect_file(DO_INI, path, {"s": {"a": "1"}, "empty": {}, "none": None}) == ([], None, 1)


@needs_do_ini
def test_file_without_trailing_newline_is_all_pending(tmp_path):
    path = write(tmp_path, "[s]\na = 1")
    pending, _, _ = module.inspect_file(DO_INI, path, {"s": {"a": "1", "b": "2"}})
    assert pending == [["s", ["a", "b"]]]


@needs_do_ini
@pytest.mark.parametrize("case", ["missing", "symlink", "directory"])
def test_files_the_probe_cannot_vouch_for_are_unsupported(tmp_path, case):
    path = str(tmp_path / "server.conf")
    if case == "symlink":
        os.symlink(write(tmp_path, "[s]\na = 1\n", "real.conf"), path)
    elif case == "directory":
        os.mkdir(path)
    pending, reason, _ = module.inspect_file(DO_INI, path, {"s": {"a": "1"}})
    assert pending is None and reason


def test_ini_file_rejecting_input_is_unsupported(tmp_path):
    path = write(tmp_path, "[s]\na = 1\n")

    def do_ini(mod, filename, **kwargs):
        mod.fail_json(msg="no")

    pending, reason, _ = module.inspect_file(do_ini, path, {"s": {"a": "1"}})
    assert pending is None and "rejected" in reason


STANZAS = {"general": {"serverName": "idx-1", "site": "site1"}, "sslConfig": {"v": "tls1.2"}, "empty": {}}
PATH = "/opt/splunk/etc/system/local/server.conf"


def probe(pending, supported=True):
    return {"changed": False, "files": {PATH: {"supported": supported, "reason": None, "pending": pending}}}


@pytest.mark.parametrize("result", [
    {"failed": False, "msg": "MODULE FAILURE", "rc": 137}, {"files": {}}, probe([], supported=False),
], ids=["module_failure", "path_missing", "unsupported"])
def test_untrusted_probe_writes_every_option(result):
    assert filters.pending_stanzas(STANZAS, result, PATH) == STANZAS
    assert not filters.probe_supported(result, PATH, STANZAS)


def test_probe_narrows_writes_to_pending_options():
    result = probe([["general", ["site"]]])
    assert filters.pending_stanzas(STANZAS, result, PATH) == {"general": {"site": "site1"}, "empty": {}}


def test_jinja2_native_writes_every_option(monkeypatch):
    monkeypatch.setattr(filters.C, "DEFAULT_JINJA2_NATIVE", True)
    result = probe([["general", ["site"]]])
    assert filters.pending_stanzas(STANZAS, result, PATH) == STANZAS
    assert not filters.probe_supported(result, PATH, STANZAS)


def test_non_string_keys_write_every_option():
    stanzas = {8000: {"x": "1"}, "settings": {"y": True}}
    assert filters.pending_stanzas(stanzas, {"files": {PATH: {"supported": True, "pending": []}}}, PATH) == stanzas
    stanzas = {"settings": {True: "1"}}
    assert filters.pending_stanzas(stanzas, {"files": {PATH: {"supported": True, "pending": []}}}, PATH) == stanzas


def test_conf_targets_match_the_original_include_vars():
    entries = [
        {"key": "server", "value": {"content": {"general": {"a": "1"}}}},
        {"key": "outputs", "value": {"directory": "", "content": {}}},
        {"key": "inputs", "value": {"directory": "/opt/splunk/etc/apps/a/local"}},
    ]
    assert filters.conf_targets(entries, "/opt/splunk/etc/system/local") == [
        {"file": "server.conf", "directory": "/opt/splunk/etc/system/local",
         "path": "/opt/splunk/etc/system/local/server.conf", "stanzas": {"general": {"a": "1"}}},
        {"file": "outputs.conf", "directory": "/opt/splunk/etc/system/local",
         "path": "/opt/splunk/etc/system/local/outputs.conf", "stanzas": {}},
        {"file": "inputs.conf", "directory": "/opt/splunk/etc/apps/a/local",
         "path": "/opt/splunk/etc/apps/a/local/inputs.conf", "stanzas": {}},
    ]


def test_conf_targets_read_non_mapping_values_as_empty_like_develop():
    # A list entry merged into map-form splunk.conf leaves {"key": "server", "value": {...}}.
    entries = [
        {"key": "key", "value": "server"},
        {"key": "value", "value": {"content": {"kvstore": {"defaultKVStoreType": "local"}}}},
        {"key": "empty", "value": None},
    ]
    assert filters.conf_targets(entries, "/opt/splunk/etc/system/local") == [
        {"file": "key.conf", "directory": "/opt/splunk/etc/system/local",
         "path": "/opt/splunk/etc/system/local/key.conf", "stanzas": {}},
        {"file": "value.conf", "directory": "/opt/splunk/etc/system/local",
         "path": "/opt/splunk/etc/system/local/value.conf",
         "stanzas": {"kvstore": {"defaultKVStoreType": "local"}}},
        {"file": "empty.conf", "directory": "/opt/splunk/etc/system/local",
         "path": "/opt/splunk/etc/system/local/empty.conf", "stanzas": {}},
    ]


def test_probe_report_has_no_values():
    report = filters.probe_report({"files": {
        PATH: {"supported": False, "reason": "symlink", "pending": []},
        "/x.conf": {"supported": True, "reason": None, "pending": [["s", ["a"]]]},
    }, "summary": {"files": 2}})
    assert report == {"summary": {"files": 2}, "unsupported": {PATH: "symlink"}}
    assert filters.probe_report({"failed": False, "msg": "MODULE FAILURE"}) == {"failed": True, "msg": "MODULE FAILURE"}
