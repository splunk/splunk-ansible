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


@pytest.mark.parametrize(
    "installed_version,writes_settings",
    [
        ("0", False),
        ("10.5.9", False),
        ("10.6.0", True),
        ("10.8.9", True),
        ("10.8.0.1", True),
        ("10.9.0", False),
        ("10.9.0.0", False),
        ("10.10.0", False),
        ("11.0.0", False),
    ],
)
@pytest.mark.parametrize("kvstore_type", ["local", "external", "cohosted"])
def test_kvstore_settings_are_written_only_before_10_9(
    installed_version, writes_settings, kvstore_type
):
    loader = DataLoader()
    tasks = loader.load_from_file(str(TASK_FILE))
    variables = {
        "kvstore_installed_splunk_version": [installed_version],
        "splunk": {"kvstore": {"default_kvstore_type": kvstore_type}},
    }
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
        conditional = Conditional(loader=loader)
        conditional.when = [task["when"]]
        templar = Templar(loader=loader, variables=variables)
        assert conditional.evaluate_conditional(templar, variables) is writes_settings
        if writes_settings:
            expected_value = (
                kvstore_type
                if task["ini_file"]["option"] == "defaultKVStoreType"
                else "false" if kvstore_type == "local" else "true"
            )
            assert str(templar.template(task["ini_file"]["value"])).lower() == expected_value
