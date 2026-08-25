#!/usr/bin/env python
"""Contract tests for role-specific Noah client configuration."""

from pathlib import Path

import pytest
import yaml
from jinja2 import Template


REPO_ROOT = Path(__file__).resolve().parents[2]
COMMON_TASKS = REPO_ROOT / "roles" / "splunk_common" / "tasks"


def load_tasks(name):
    with (COMMON_TASKS / name).open() as task_file:
        return yaml.safe_load(task_file)


def task_named(tasks, name):
    return next(task for task in tasks if task.get("name") == name)


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("splunk_indexer", "30"),
        ("splunk_search_head", "0"),
        ("splunk_deployer", "0"),
    ],
)
def test_noah_heartbeat_period_is_role_specific(role, expected):
    tasks = load_tasks("configure_noah_role.yml")
    heartbeat = task_named(tasks, "Set role-specific Noah heartbeat period")
    rendered = Template(heartbeat["ini_file"]["value"]).render(
        splunk={"role": role}
    )
    assert rendered == expected


def test_search_heads_fetch_peers_without_joining_indexer_membership():
    tasks = load_tasks("configure_noah_role.yml")

    use_peers = task_named(tasks, "Enable Noah peer discovery for search heads")
    assert use_peers["ini_file"]["section"] == "noahService"
    assert use_peers["ini_file"]["option"] == "usePeers"
    assert use_peers["ini_file"]["value"] == "true"
    assert use_peers["when"] == 'splunk.role == "splunk_search_head"'

    decouple = task_named(
        tasks, "Enable decoupled search and indexing for Noah search heads"
    )
    assert decouple["ini_file"]["section"] == "decouple_search_indexing"
    assert decouple["ini_file"]["option"] == "decoupleSearchIndexing"
    assert decouple["ini_file"]["value"] == "true"
    assert decouple["when"] == 'splunk.role == "splunk_search_head"'

    role = task_named(tasks, "Select the decoupled Noah search-head role")
    assert role["ini_file"]["section"] == "decouple_search_indexing"
    assert role["ini_file"]["option"] == "role"
    assert role["ini_file"]["value"] == "search_head"
    assert role["when"] == 'splunk.role == "splunk_search_head"'


def test_role_configuration_runs_after_defaults_and_before_splunk_start():
    tasks = load_tasks("main.yml")
    includes = [
        task["include_tasks"]
        for task in tasks
        if isinstance(task, dict) and "include_tasks" in task
    ]
    defaults_index = includes.index("set_config_file.yml")
    role_index = includes.index("configure_noah_role.yml")
    start_index = includes.index("start_splunk.yml")
    assert defaults_index < role_index < start_index
