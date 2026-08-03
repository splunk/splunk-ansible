"""Regression checks for stable indexer search-address registration."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_FILE = (
    REPO_ROOT
    / "roles"
    / "splunk_common"
    / "tasks"
    / "configure_indexer_search_address_prestart.yml"
)
COMMON_MAIN = REPO_ROOT / "roles" / "splunk_common" / "tasks" / "main.yml"


def _task(name):
    tasks = yaml.safe_load(TASK_FILE.read_text(encoding="utf-8"))
    return next(task for task in tasks if task.get("name") == name)


def test_stable_search_address_is_written_without_requesting_a_restart():
    task = _task("Configure the stable indexer search address before Splunk starts")

    assert task["ini_file"]["section"] == "clustering"
    assert task["ini_file"]["option"] == "register_search_address"
    assert task["ini_file"]["value"] == "{{ splunk.idxc.register_search_address }}"
    assert "notify" not in task
    assert task["when"] == 'splunk.idxc.register_search_address != "absent"'


def test_absent_value_removes_only_the_registered_search_address():
    task = _task("Remove the registered indexer search address before Splunk starts")

    assert task["ini_file"]["section"] == "clustering"
    assert task["ini_file"]["option"] == "register_search_address"
    assert task["ini_file"]["state"] == "absent"
    assert "notify" not in task
    assert task["when"] == 'splunk.idxc.register_search_address == "absent"'


def test_effective_configuration_is_verified_before_start():
    tasks = yaml.safe_load(TASK_FILE.read_text(encoding="utf-8"))
    names = [task.get("name") for task in tasks]

    assert names.index("Configure the stable indexer search address before Splunk starts") < names.index(
        "Read the effective registered indexer search address"
    )
    assert names.index("Read the effective registered indexer search address") < names.index(
        "Verify the effective registered indexer search address"
    )


def test_absent_value_is_verified_before_start():
    task = _task("Verify the registered indexer search address is absent")

    assert task["when"] == 'splunk.idxc.register_search_address == "absent"'
    assert task["assert"]["that"] == [
        "'register_search_address =' not in indexer_search_address_btool.stdout"
    ]


def test_common_role_runs_configuration_before_splunk_start():
    tasks = yaml.safe_load(COMMON_MAIN.read_text(encoding="utf-8"))
    includes = [task.get("include_tasks") for task in tasks]
    task = next(
        task
        for task in tasks
        if task.get("include_tasks") == "configure_indexer_search_address_prestart.yml"
    )

    assert includes.index("configure_indexer_search_address_prestart.yml") < includes.index(
        "start_splunk.yml"
    )
    assert task["when"] == [
        'splunk.role == "splunk_indexer"',
        "splunk_indexer_cluster | bool",
        'splunk.idxc.register_search_address | default("", true) | length > 0',
    ]
