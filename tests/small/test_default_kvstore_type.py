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
@pytest.mark.parametrize("kvstore_type", [None, "", "local", "external", "cohosted"])
def test_kvstore_settings_version_boundaries(
    installed_version, writes_settings, kvstore_type
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
            expected_value = "local" if is_type else "false"
            templar = Templar(loader=loader, variables=variables)
            assert str(templar.template(task["ini_file"]["value"])).lower() == expected_value


@pytest.mark.parametrize(
    "kvstore,role,included",
    [
        ({"default_kvstore_type": "local"}, "splunk_standalone", True),
        ({"kvservice_connection_string": "https://kvservice"}, "splunk_standalone", True),
        ({"default_kvstore_type": None, "kvservice_connection_string": "https://kvservice"}, "splunk_standalone", True),
        ({}, "splunk_standalone", True),
        ({"default_kvstore_type": "", "kvservice_connection_string": ""}, "splunk_standalone", True),
        ({"default_kvstore_type": "local"}, "splunk_universal_forwarder", False),
    ],
)
def test_enterprise_kvstore_policy_does_not_require_an_explicit_type(kvstore, role, included):
    loader = DataLoader()
    tasks = loader.load_from_file(str(TASK_FILE.with_name("main.yml")))
    policy_tasks = [
        task for task in tasks
        if task.get("include_tasks") == "set_default_kvstore_type.yml"
    ]
    assert len(policy_tasks) == 2
    for task in policy_tasks:
        assert _condition(loader, task, {"splunk": {"kvstore": kvstore, "role": role}}) is included


def test_policy_runs_before_early_commands_and_after_generic_config():
    tasks = DataLoader().load_from_file(str(TASK_FILE.with_name("main.yml")))
    includes = [task.get("include_tasks") for task in tasks]
    policy_indices = [
        i for i, include in enumerate(includes)
        if include == "set_default_kvstore_type.yml"
    ]
    assert policy_indices[0] < includes.index("enable_admin_auth.yml")
    assert policy_indices[0] < includes.index("pre_splunk_start_commands.yml")
    config_indices = [
        i for i, include in enumerate(includes)
        if include == "set_config_file.yml"
    ]
    assert len(config_indices) == 2
    assert config_indices[0] < policy_indices[0]
    assert config_indices[1] < policy_indices[1]
    assert policy_indices[1] < includes.index("configure_shc_prestart.yml")
    assert policy_indices[1] < includes.index("start_splunk.yml")


@pytest.mark.parametrize(
    "system,pid_exists,probes_status",
    [("Linux", False, False), ("Linux", True, True), ("Win32NT", False, True)],
)
def test_stopping_fresh_linux_install_does_not_consume_first_time_run(
    system, pid_exists, probes_status
):
    loader = DataLoader()
    tasks = loader.load_from_file(str(TASK_FILE.with_name("stop_splunk.yml")))
    status = next(task for task in tasks if task.get("name") == "Get Splunk status")
    variables = {
        "ansible_system": system,
        "stop_splunk_pid": {"stat": {"exists": pid_exists}},
    }
    assert _condition(loader, status, variables) is probes_status
