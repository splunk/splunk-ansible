"""Version boundaries for Ansible-managed KV Store settings."""

from pathlib import Path

import pytest
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar


TASK_FILE = (
    Path(__file__).resolve().parents[2]
    / "roles"
    / "splunk_common"
    / "tasks"
    / "set_default_kvstore_type.yml"
)


def _condition(loader, task, variables):
    conditional = Conditional(loader=loader)
    conditions = task["when"]
    conditional.when = conditions if isinstance(conditions, list) else [conditions]
    return conditional.evaluate_conditional(
        Templar(loader=loader, variables=variables), variables
    )


@pytest.mark.parametrize(
    "installed_version,writes_type,writes_startup,is_10_9_or_later",
    [
        ("0", False, False, False),
        ("10.5.9", False, False, False),
        ("10.6.0", True, True, False),
        ("10.8.9", True, True, False),
        ("10.8.0.1", True, True, False),
        ("10.9.0", False, True, True),
        ("10.9.0.0", False, True, True),
        ("10.10.0", False, True, True),
        ("11.0.0", False, True, True),
    ],
)
@pytest.mark.parametrize("kvstore_type", ["local", "external", "cohosted", None, ""])
def test_kvstore_settings_version_boundaries(
    installed_version, writes_type, writes_startup, is_10_9_or_later, kvstore_type
):
    loader = DataLoader()
    tasks = loader.load_from_file(str(TASK_FILE))
    kvstore = {"kvservice_connection_string": "https://kvservice"}
    if kvstore_type is not None:
        kvstore["default_kvstore_type"] = kvstore_type
    variables = {
        "kvstore_installed_splunk_version": [installed_version],
        "splunk": {"kvstore": kvstore, "role": "splunk_standalone"},
    }
    support_task = next(
        task for task in tasks
        if task["name"] == "Set default KV Store type support fact"
    )
    variables["kvstore_default_type_supported"] = Templar(
        loader=loader, variables=variables
    ).template(support_task["set_fact"]["kvstore_default_type_supported"])

    validation = next(task for task in tasks if "assert" in task)
    assert _condition(loader, validation, variables) is bool(kvstore_type)

    write_tasks = [task for task in tasks if "ini_file" in task]
    assert {task["ini_file"]["option"] for task in write_tasks} == {
        "defaultKVStoreType", "postgresMigrateOnStartup",
    }
    for task in write_tasks:
        is_type = task["ini_file"]["option"] == "defaultKVStoreType"
        expected_write = (
            writes_type and bool(kvstore_type)
            if is_type
            else writes_startup and (bool(kvstore_type) or is_10_9_or_later)
        )
        assert _condition(loader, task, variables) is expected_write
        if expected_write:
            expected_value = (
                kvstore_type if is_type
                else "false" if kvstore_type == "local" and not is_10_9_or_later
                else "true"
            )
            templar = Templar(loader=loader, variables=variables)
            assert str(templar.template(task["ini_file"]["value"])).lower() == expected_value


@pytest.mark.parametrize(
    "kvstore,role,included",
    [
        ({"default_kvstore_type": "local"}, "splunk_standalone", True),
        ({"kvservice_connection_string": "https://kvservice"}, "splunk_standalone", True),
        ({"default_kvstore_type": None, "kvservice_connection_string": "https://kvservice"}, "splunk_standalone", True),
        ({}, "splunk_standalone", False),
        ({"default_kvstore_type": "", "kvservice_connection_string": ""}, "splunk_standalone", False),
        ({"kvservice_connection_string": "https://kvservice"}, "splunk_universal_forwarder", False),
    ],
)
def test_kvstore_tasks_run_for_type_or_connection(kvstore, role, included):
    loader = DataLoader()
    tasks = loader.load_from_file(str(TASK_FILE.with_name("main.yml")))
    task = next(
        task for task in tasks
        if task.get("include_tasks") == "set_default_kvstore_type.yml"
    )
    assert _condition(loader, task, {"splunk": {"kvstore": kvstore, "role": role}}) is included
