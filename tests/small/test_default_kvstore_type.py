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
    "installed_version,writes_unmanaged,writes_managed",
    [
        ("0", False, False),
        ("10.5.9", False, False),
        ("10.6.0", True, True),
        ("10.6.7.1", True, True),
        ("10.7.0", True, False),
        ("10.8.9", True, False),
        ("10.8.0.1", True, False),
        ("10.9.0", True, False),
        ("10.9.0.0", True, False),
        ("10.10.0", True, False),
        ("11.0.0", True, False),
    ],
)
@pytest.mark.parametrize("kvstore_type", ["local", "external", "cohosted"])
@pytest.mark.parametrize("enabled", [None, False, True])
def test_kvstore_settings_version_boundaries(
    installed_version, writes_unmanaged, writes_managed, kvstore_type, enabled
):
    loader = DataLoader()
    tasks = loader.load_from_file(str(TASK_FILE))
    variables = {
        "kvstore_installed_splunk_version": [installed_version],
        "splunk": {
            "kvstore": {"default_kvstore_type": kvstore_type},
            "role": "splunk_standalone",
        },
    }
    if enabled is not None:
        variables["splunk_kvservice_enabled"] = enabled
    writes_settings = writes_unmanaged if enabled is None else writes_managed
    support_task = next(
        task for task in tasks
        if task["name"] == "Set default KV Store type support fact"
    )
    variables["kvstore_default_type_supported"] = Templar(
        loader=loader, variables=variables
    ).template(support_task["set_fact"]["kvstore_default_type_supported"])

    write_tasks = [task for task in tasks if "ini_file" in task]
    assert {task["ini_file"]["option"] for task in write_tasks} == {
        "defaultKVStoreType", "postgresMigrateOnStartup",
    }
    for task in write_tasks:
        is_type = task["ini_file"]["option"] == "defaultKVStoreType"
        assert _condition(loader, task, variables) is writes_settings
        if writes_settings:
            expected_value = (
                kvstore_type if is_type
                else "false" if kvstore_type == "local"
                else "true"
            )
            templar = Templar(loader=loader, variables=variables)
            assert str(templar.template(task["ini_file"]["value"])).lower() == expected_value


@pytest.mark.parametrize(
    "kvstore,role,included",
    [
        ({"default_kvstore_type": "local"}, "splunk_standalone", True),
        ({"kvservice_connection_string": "https://kvservice"}, "splunk_standalone", False),
        ({"default_kvstore_type": None, "kvservice_connection_string": "https://kvservice"}, "splunk_standalone", False),
        ({}, "splunk_standalone", False),
        ({"default_kvstore_type": "", "kvservice_connection_string": ""}, "splunk_standalone", False),
        ({"default_kvstore_type": "local"}, "splunk_universal_forwarder", False),
    ],
)
def test_kvstore_tasks_require_an_explicit_default_type(kvstore, role, included):
    loader = DataLoader()
    tasks = loader.load_from_file(str(TASK_FILE.with_name("main.yml")))
    includes = [
        task for task in tasks
        if task.get("include_tasks") == "set_default_kvstore_type.yml"
    ]
    variables = {"splunk": {"kvstore": kvstore, "role": role}}
    assert sum(_condition(loader, task, variables) for task in includes) == int(included)


@pytest.mark.parametrize("enabled", [True, False])
def test_explicit_kvservice_policy_still_includes_legacy_version_check(enabled):
    loader = DataLoader()
    tasks = loader.load_from_file(str(TASK_FILE.with_name("main.yml")))
    includes = [
        task for task in tasks
        if task.get("include_tasks") == "set_default_kvstore_type.yml"
    ]
    variables = {
        "splunk_kvservice_enabled": enabled,
        "splunk": {"role": "splunk_standalone", "kvstore": {"default_kvstore_type": "external"}},
    }
    assert sum(_condition(loader, task, variables) for task in includes) == 1
