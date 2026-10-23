#!/usr/bin/env python
"""Unit tests for ConfigMap receipt reconciliation in roles/splunk_common."""

from __future__ import absolute_import

import os
import sys

import pytest
import yaml

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_DIR = os.path.join(FILE_DIR, "..", "..")
TASKS_DIR = os.path.join(REPO_DIR, "roles", "splunk_common", "tasks")
sys.path.insert(0, os.path.join(REPO_DIR, "roles", "splunk_common", "filter_plugins"))

import config_map_receipts  # noqa: E402

dropped_options = config_map_receipts.FilterModule().filters()["config_map_dropped_options"]


def load_tasks(name):
    with open(os.path.join(TASKS_DIR, name)) as stream:
        return yaml.safe_load(stream)


def named_task(tasks, prefix):
    return next(task for task in tasks if task.get("name", "").startswith(prefix))


def test_unchanged_config_drops_nothing():
    stanzas = {
        "general": {"serverName": "idx-1", "pass4SymmKey": "s3cret"},
        "sslConfig": {"sslVerifyServerCert": "false"},
    }

    assert dropped_options(stanzas, dict(stanzas)) == {}


def test_changed_value_is_not_dropped():
    previous = {"kvstore": {"disabled": True, "port": 8191}}
    desired = {"kvstore": {"disabled": False, "port": 8191}}

    assert dropped_options(previous, desired) == {}


def test_only_options_missing_from_desired_config_are_dropped():
    previous = {
        "kvstore": {"disabled": True, "port": 8191},
        "obsolete": {"option": "x"},
        "general": {"serverName": "idx-1"},
    }
    desired = {
        "kvstore": {"disabled": False},
        "general": {"serverName": "idx-1"},
        "new": {"option": "y"},
    }

    assert dropped_options(previous, desired) == {
        "kvstore": {"port": 8191},
        "obsolete": {"option": "x"},
    }


def test_unowned_options_are_never_dropped():
    previous = {"kvstore": {"disabled": True}}

    dropped = dropped_options(previous, {})

    assert dropped == {"kvstore": {"disabled": True}}
    assert "general" not in dropped


def test_first_run_has_nothing_to_drop():
    assert dropped_options({}, {"general": {"serverName": "idx-1"}}) == {}


@pytest.mark.parametrize("desired", [{}, None])
def test_all_desired_settings_removed_drops_every_recorded_option(desired):
    previous = {"settings": {"a": "1", "b": "2"}, "other": {"c": "3"}}

    assert dropped_options(previous, desired) == previous


def test_header_only_stanza_drops_its_recorded_options():
    previous = {"settings": {"a": "1"}}

    assert dropped_options(previous, {"settings": None}) == {"settings": {"a": "1"}}
    assert dropped_options(previous, {"settings": {}}) == {"settings": {"a": "1"}}


@pytest.mark.parametrize("previous", [None, "", [], {"header_only": None}, {"header_only": {}}])
def test_empty_or_header_only_receipts_drop_nothing(previous):
    assert dropped_options(previous, {}) == {}


def test_removal_loop_uses_only_dropped_options_from_this_files_receipt():
    tasks = load_tasks("reconcile_config_map_values.yml")
    load = named_task(tasks, "Load previous ConfigMap-owned values")
    remove = named_task(tasks, "Remove dropped ConfigMap-owned values")

    assert "slurp" in load
    assert load["register"] == "config_map_managed_values"
    assert load["no_log"] == "{{ hide_password }}"
    assert not any("include_vars" in task for task in tasks)
    assert "config_map_managed_values.content | b64decode | from_yaml" in remove["with_dict"]
    assert "config_map_dropped_options(conf_stanzas)" in remove["with_dict"]


def test_targets_with_no_desired_settings_are_still_reconciled():
    tasks = load_tasks("set_config_file.yml")
    reconcile = named_task(tasks, "Remove stale ConfigMap-owned values")
    record = named_task(tasks, "Record ConfigMap-owned values")
    forget = named_task(tasks, "Remove ConfigMap ownership record")

    assert reconcile["when"] == "reconcile_config_map_values | default(false) | bool"
    assert "conf_stanzas | length > 0" in record["when"]
    assert "conf_stanzas | length == 0" in forget["when"]
    assert forget["file"] == {
        "path": "{{ conf_directory }}/.{{ conf_file }}.splunk-ansible-managed.yml",
        "state": "absent",
    }
    assert forget["become_user"] == "{{ splunk.user }}"
