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


def _tasks():
    return yaml.safe_load(TASK_FILE.read_text(encoding="utf-8"))


def _task(name):
    return next(task for task in _tasks() if task.get("name") == name)


def test_stable_search_address_is_written_without_requesting_a_restart():
    task = _task("Configure the stable indexer search address before Splunk starts")

    assert task["ini_file"]["section"] == "clustering"
    assert task["ini_file"]["option"] == "register_search_address"
    assert task["ini_file"]["value"] == "{{ splunk.idxc.register_search_address }}"
    assert "notify" not in task
    assert task["when"] == [
        'indexer_search_address_mode != "absent"',
        "indexer_search_address_should_manage | bool",
    ]


def test_automatic_value_preserves_unmanaged_effective_configuration():
    action = _task("Select stable indexer search-address action")
    verify = _task("Verify an existing customer indexer search address is preserved")

    expression = action["set_fact"]["indexer_search_address_should_manage"]
    assert "indexer_search_address_mode == 'auto'" in expression
    assert "indexer_search_address_owned" in expression
    assert "'register_search_address =' not in" in expression
    assert verify["when"] == [
        'indexer_search_address_mode == "auto"',
        "indexer_search_address_exists | bool",
        "not indexer_search_address_should_manage | bool",
    ]
    assert verify["assert"]["that"] == [
        "indexer_search_address_before.stdout == indexer_search_address_btool.stdout"
    ]


def test_managed_value_records_persistent_ownership():
    task = _task("Record stable indexer search-address ownership")

    assert task["copy"]["dest"] == "{{ indexer_search_address_marker }}"
    assert task["copy"]["content"] == "{{ splunk.idxc.register_search_address }}\n"
    assert task["copy"]["mode"] == 0o600
    assert task["when"] == [
        'indexer_search_address_mode != "absent"',
        "indexer_search_address_should_manage | bool",
    ]


def test_absent_value_removes_only_an_owned_setting():
    remove = _task("Remove the managed indexer search address before Splunk starts")
    marker = _task("Remove obsolete stable indexer search-address ownership marker")
    verify = _task("Verify controlled rollback removed only managed ownership")

    assert remove["ini_file"]["section"] == "clustering"
    assert remove["ini_file"]["option"] == "register_search_address"
    assert remove["ini_file"]["state"] == "absent"
    assert "notify" not in remove
    expected_when = [
        'indexer_search_address_mode == "absent"',
        "indexer_search_address_owned | bool",
    ]
    assert remove["when"] == expected_when
    assert marker["when"] == [
        "indexer_search_address_marker_before.stat.exists",
        'indexer_search_address_mode == "absent" or not indexer_search_address_owned | bool',
    ]
    assert verify["when"] == 'indexer_search_address_mode == "absent"'
    assert verify["assert"]["that"] == [
        "not indexer_search_address_marker_after.stat.exists"
    ]


def test_ownership_requires_effective_value_to_match_marker():
    classify = _task("Classify the effective indexer search address")
    preserve = _task("Verify controlled rollback preserved an unowned customer value")

    expression = classify["set_fact"]["indexer_search_address_owned"]
    assert "indexer_search_address_marker_before.stat.exists" in expression
    assert "indexer_search_address_marker_value" in expression
    assert "indexer_search_address_marker_value | length > 0" in expression
    assert "indexer_search_address_before.stdout" in expression
    assert preserve["when"] == [
        'indexer_search_address_mode == "absent"',
        "indexer_search_address_exists | bool",
        "not indexer_search_address_owned | bool",
    ]


def test_effective_configuration_is_verified_before_start():
    names = [task.get("name") for task in _tasks()]

    assert names.index("Read the existing effective indexer search address") < names.index(
        "Configure the stable indexer search address before Splunk starts"
    )
    assert names.index("Configure the stable indexer search address before Splunk starts") < names.index(
        "Read the effective registered indexer search address"
    )
    assert names.index("Read the effective registered indexer search address") < names.index(
        "Verify the managed registered indexer search address"
    )


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
