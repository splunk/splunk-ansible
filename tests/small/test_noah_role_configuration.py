#!/usr/bin/env python
"""Contract tests for role-specific Noah client configuration."""

from pathlib import Path

import pytest
import yaml
from jinja2 import Template


REPO_ROOT = Path(__file__).resolve().parents[2]
COMMON_TASKS = REPO_ROOT / "roles" / "splunk_common" / "tasks"
COMMON_HANDLERS = REPO_ROOT / "roles" / "splunk_common" / "handlers"


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


def test_prestart_shc_configuration_uses_the_splunk_shclustering_stanza():
    tasks = load_tasks("configure_noah.yml")
    shc_tasks = [
        task
        for task in tasks
        if isinstance(task, dict)
        and isinstance(task.get("ini_file"), dict)
        and task["ini_file"].get("option")
        in {
            "register_replication_address",
            "search_head_uri",
            "shcluster_label",
            "replication_factor",
            "conf_deploy_fetch_url",
            "mgmt_uri",
        }
    ]
    assert shc_tasks
    assert {task["ini_file"]["section"] for task in shc_tasks} == {
        "shclustering"
    }
    assert "shcclustering" not in (COMMON_TASKS / "configure_noah.yml").read_text()


def test_prestart_shc_configuration_creates_a_replication_listener_stanza():
    tasks = load_tasks("configure_noah.yml")
    listener = task_named(tasks, "Write SHC replication port listener pre-start")
    assert listener["ini_file"]["section"] == (
        "replication_port://{{ splunk.shc.replication_port }}"
    )
    assert listener["ini_file"]["option"] == "disabled"
    assert listener["ini_file"]["value"] == "false"
    assert "conf_replication_port" not in (
        COMMON_TASKS / "configure_noah.yml"
    ).read_text()


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


def test_noah_cli_restart_uses_bounded_stop_start_without_changing_classic():
    with (COMMON_HANDLERS / "restart_splunk.yml").open() as handler_file:
        handlers = yaml.safe_load(handler_file)

    noah_restart = task_named(
        handlers,
        "Restart Noah-managed splunkd service - Via bounded CLI stop and start",
    )
    assert "shell" in noah_restart
    assert " stop --answer-yes" in noah_restart["shell"]
    assert " start --answer-yes --accept-license" in noah_restart["shell"]
    assert " restart " not in noah_restart["shell"]
    assert "splunk.conf.server.content.noahService is defined" in noah_restart["when"]

    classic_restart = task_named(
        handlers, "Restart classic splunkd service - Via CLI"
    )
    assert classic_restart["command"].endswith(
        "restart --answer-yes --accept-license"
    )
    assert any("noahService is defined" in condition for condition in classic_restart["when"])
