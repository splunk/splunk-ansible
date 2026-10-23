#!/usr/bin/env python
"""Unit tests for combining list-form splunk.conf entries by effective file."""

from __future__ import absolute_import

import ast
import copy
import os
import sys

import jinja2
import pytest
import yaml

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_DIR = os.path.join(FILE_DIR, "..", "..")
sys.path.insert(0, os.path.join(REPO_DIR, "inventory"))
sys.path.insert(0, os.path.join(REPO_DIR, "roles", "splunk_common", "filter_plugins"))

import environ  # noqa: E402
import splunk_conf  # noqa: E402

SYSTEM_LOCAL = "/opt/splunk/etc/system/local"
SOK_LOCAL = "/opt/splunk/etc/apps/100-sok/local"

combine = splunk_conf.FilterModule().filters()["normalize_splunk_conf_entries"]


def entry(key, content, directory=None):
    value = {"content": content}
    if directory is not None:
        value["directory"] = directory
    return {"key": key, "value": value}


def test_entries_for_the_same_file_are_merged_into_one():
    entries = [
        entry("outputs", {"cloud_processing_queue": {"remote_queue.type": "sqs_smartbus"}}, SOK_LOCAL),
        entry("outputs", {"remote_queue:sok_queue": {"remote_queue.type": "sqs_smartbus"}}, SOK_LOCAL),
    ]

    combined = combine(entries, SYSTEM_LOCAL)

    assert combined == [entry("outputs", {
        "cloud_processing_queue": {"remote_queue.type": "sqs_smartbus"},
        "remote_queue:sok_queue": {"remote_queue.type": "sqs_smartbus"},
    }, SOK_LOCAL)]


def test_later_entry_wins_conflicting_options():
    entries = [
        entry("outputs", {"tcpout": {"indexAndForward": "false", "maxQueueSize": "10MB"}}, SOK_LOCAL),
        entry("outputs", {"tcpout": {"indexAndForward": "true"}}, SOK_LOCAL),
        entry("outputs", {"tcpout": {"maxQueueSize": "auto"}}, SOK_LOCAL),
    ]

    combined = combine(entries, SYSTEM_LOCAL)

    assert combined[0]["value"]["content"] == {
        "tcpout": {"indexAndForward": "true", "maxQueueSize": "auto"},
    }
    # Deterministic: same input, same result.
    assert combine(entries, SYSTEM_LOCAL) == combined


def test_combined_entry_keeps_the_first_entry_position():
    entries = [
        entry("outputs", {"a": {"x": "1"}}, SOK_LOCAL),
        entry("inputs", {"b": {"y": "1"}}, SOK_LOCAL),
        entry("outputs", {"c": {"z": "1"}}, SOK_LOCAL),
    ]

    combined = combine(entries, SYSTEM_LOCAL)

    assert [e["key"] for e in combined] == ["outputs", "inputs"]
    assert combined[0]["value"]["content"] == {"a": {"x": "1"}, "c": {"z": "1"}}


def test_different_directories_and_files_are_kept_separate():
    entries = [
        entry("server", {"general": {"serverName": "idx"}}),
        entry("server", {"general": {"parallelIngestionPipelines": "2"}}, "/opt/splunk/etc/apps/app1/local"),
        entry("web", {"settings": {"enableSplunkWebSSL": "true"}}),
        entry("outputs", {"tcpout": {"defaultGroup": "a"}}, "/opt/splunk/etc/apps/app1/local"),
        entry("outputs", {"tcpout": {"defaultGroup": "b"}}, "/opt/splunk/etc/apps/app2/local"),
    ]

    assert combine(entries, SYSTEM_LOCAL) == entries


def test_default_and_explicit_spellings_of_one_directory_are_merged():
    entries = [
        entry("server", {"general": {"serverName": "idx"}}),
        entry("server", {"sslConfig": {"sslVersions": "tls1.2"}}, SYSTEM_LOCAL + "/"),
        entry("server", {"kvstore": {"disabled": "true"}}, "/opt/splunk/etc/./system//local"),
    ]

    combined = combine(entries, SYSTEM_LOCAL)

    assert len(combined) == 1
    assert combined[0]["value"]["content"] == {
        "general": {"serverName": "idx"},
        "sslConfig": {"sslVersions": "tls1.2"},
        "kvstore": {"disabled": "true"},
    }


def test_combining_does_not_mutate_the_input():
    entries = [
        entry("outputs", {"tcpout": {"defaultGroup": "a"}}, SOK_LOCAL),
        entry("outputs", {"tcpout": {"defaultGroup": "b"}}, SOK_LOCAL),
    ]
    original = copy.deepcopy(entries)

    combine(entries, SYSTEM_LOCAL)

    assert entries == original


def test_dict_form_conf_is_returned_untouched():
    dict_conf = {
        "server": {"content": {"general": {"serverName": "idx"}}},
        "web": {"directory": "/opt/splunk/etc/apps/app1/local", "content": {"settings": {}}},
    }
    original = copy.deepcopy(dict_conf)

    assert combine(dict_conf, SYSTEM_LOCAL) is dict_conf
    assert dict_conf == original


def test_malformed_entries_pass_through_unchanged():
    entries = [
        "not-a-mapping",
        {"key": "server"},
        {"value": {"content": {"general": {"a": "1"}}}},
        entry("server", {"general": {"a": "1"}}),
    ]

    assert combine(entries, SYSTEM_LOCAL) == entries


def noah_entries():
    return [
        entry("server", {"noahService": {"uri": "https://noah.example"}}),
        entry("outputs", {"tcpout": {"defaultGroup": "a"}}, SOK_LOCAL),
        entry("server", {"noahService": {"pass4SymmKey": "noah-secret"}}),
        entry("outputs", {"tcpout": {"useACK": "true"}}, SOK_LOCAL),
        entry("server", {"general": {"site": "site1"}}, "/opt/splunk/etc/apps/app1/local"),
    ]


def server_entries(entries):
    return [e for e in entries if e["key"] == "server"]


def test_noah_normalization_still_merges_only_server_conf():
    vars_scope = {
        "splunk_noah_enabled": True,
        "splunk": {"home": "/opt/splunk", "conf": noah_entries()},
    }

    environ.normalizeNoahConf(vars_scope)

    assert [e["key"] for e in vars_scope["splunk"]["conf"]] == ["server", "outputs", "outputs", "server"]


def test_combining_noah_effective_conf_leaves_its_server_entries_unchanged():
    vars_scope = {
        "splunk_noah_enabled": True,
        "splunk": {"home": "/opt/splunk", "conf": noah_entries()},
    }
    environ.normalizeNoahConf(vars_scope)
    splunk_conf_effective = vars_scope["splunk"]["conf"]

    combined = combine(splunk_conf_effective, SYSTEM_LOCAL)

    assert server_entries(combined) == server_entries(splunk_conf_effective)
    assert server_entries(combined)[0]["value"]["content"]["noahService"] == {
        "uri": "https://noah.example",
        "pass4SymmKey": "noah-secret",
    }
    assert combined == combine(noah_entries(), SYSTEM_LOCAL)


# ---------------------------------------------------------------------------
# Wiring in roles/splunk_common/tasks/main.yml
# ---------------------------------------------------------------------------

def main_tasks():
    with open(os.path.join(REPO_DIR, "roles", "splunk_common", "tasks", "main.yml")) as stream:
        return yaml.safe_load(stream)


def writer_loop_items(splunk, splunk_conf_by_file=None):
    """Render the set_config_file.yml loop expression from main.yml."""
    task = next(t for t in main_tasks() if t.get("include_tasks") == "set_config_file.yml")
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    env.filters["dict2items"] = lambda d: [{"key": k, "value": v} for k, v in d.items()]
    env.tests["mapping"] = lambda value: isinstance(value, dict)
    context = {"splunk": splunk}
    if splunk_conf_by_file is not None:
        context["splunk_conf_by_file"] = splunk_conf_by_file
    return ast.literal_eval(env.from_string(task["with_items"]).render(**context))


def test_combine_task_runs_before_the_writer_loop_for_list_form_only():
    tasks = main_tasks()
    names = [t.get("name") for t in tasks]
    combine_index = names.index("Combine list-form splunk.conf entries by effective file")
    writer_index = next(i for i, t in enumerate(tasks) if t.get("include_tasks") == "set_config_file.yml")
    noah_index = next(i for i, t in enumerate(tasks)
                      if t.get("include_role", {}).get("tasks_from") == "pre_auth")
    combine_task = tasks[combine_index]

    assert noah_index < combine_index < writer_index
    assert "splunk_conf_effective | default(splunk.conf)" in combine_task["set_fact"]["splunk_conf_by_file"]
    assert "normalize_splunk_conf_entries(splunk.home + '/etc/system/local')" in (
        combine_task["set_fact"]["splunk_conf_by_file"])
    assert "splunk.conf is not mapping" in combine_task["when"]
    assert combine_task["no_log"] == "{{ hide_password }}"


def test_writer_loop_uses_combined_entries_for_list_form():
    combined = combine(noah_entries(), SYSTEM_LOCAL)

    assert writer_loop_items({"conf": noah_entries()}, combined) == combined


@pytest.mark.parametrize("conf", [[], None])
def test_writer_loop_tolerates_empty_conf_without_combined_fact(conf):
    assert writer_loop_items({"conf": conf}) == conf


def test_writer_loop_keeps_dict_form_conf():
    dict_conf = {"server": {"content": {"general": {"serverName": "idx"}}}}

    assert writer_loop_items({"conf": dict_conf}, ["ignored"]) == [
        {"key": "server", "value": dict_conf["server"]},
    ]
