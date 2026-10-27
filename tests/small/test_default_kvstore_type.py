"""Version boundaries for Ansible-managed KV Store settings."""

import configparser
import getpass
import grp
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml
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
@pytest.mark.parametrize(
    "kvstore,kvstore_type",
    [
        (None, None),
        ({}, None),
        ({"default_kvstore_type": None}, None),
        ({"default_kvstore_type": ""}, None),
        ({"kvservice_scope": "deployment"}, None),
        ({"default_kvstore_type": "local"}, "local"),
        ({"default_kvstore_type": "external"}, "external"),
        ({"default_kvstore_type": "cohosted"}, "cohosted"),
    ],
)
def test_kvstore_settings_version_boundaries(
    installed_version, writes_type, writes_startup, is_10_9_or_later,
    kvstore, kvstore_type,
):
    loader = DataLoader()
    tasks = loader.load_from_file(str(TASK_FILE))
    variables = {
        "kvstore_installed_splunk_version": [installed_version],
        "splunk": {"role": "splunk_standalone"},
    }
    if kvstore is not None:
        variables["splunk"]["kvstore"] = kvstore
    for task in tasks:
        if "set_fact" in task and "kvstore_installed_splunk_version" not in task["set_fact"]:
            variables.update(Templar(loader=loader, variables=variables).template(task["set_fact"]))

    write_tasks = [task for task in tasks if "ini_file" in task]
    assert {task["ini_file"]["option"] for task in write_tasks} == {
        "defaultKVStoreType", "postgresMigrateOnStartup",
    }
    for task in write_tasks:
        is_type = task["ini_file"]["option"] == "defaultKVStoreType"
        expected_write = (
            writes_type and kvstore_type is not None if is_type
            else writes_startup and (is_10_9_or_later or kvstore_type is not None)
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
        ({"kvservice_scope": "deployment"}, "splunk_standalone", True),
        ({"default_kvstore_type": None}, "splunk_standalone", True),
        ({}, "splunk_standalone", True),
        ({"default_kvstore_type": ""}, "splunk_standalone", True),
        ({"default_kvstore_type": "local"}, "splunk_universal_forwarder", False),
        ({}, "splunk_universal_forwarder", False),
    ],
)
def test_kvstore_tasks_run_for_enterprise_without_a_default_type(kvstore, role, included):
    loader = DataLoader()
    tasks = loader.load_from_file(str(TASK_FILE.with_name("main.yml")))
    task = next(
        task for task in tasks
        if task.get("include_tasks") == "set_default_kvstore_type.yml"
    )
    assert _condition(loader, task, {"splunk": {"kvstore": kvstore, "role": role}}) is included


def test_upgrade_resets_saved_migration_flag_without_a_default_type(tmp_path):
    local = tmp_path / "etc/system/local"
    local.mkdir(parents=True)
    config_path = local / "server.conf"
    config_path.write_text(
        "[kvstore]\ndefaultKVStoreType = local\npostgresMigrateOnStartup = false\n"
    )
    version_path = tmp_path / "version"
    splunk_exec = tmp_path / "splunk"
    splunk_exec.write_text(
        "#!{}\nfrom pathlib import Path\n"
        "print('Splunk ' + Path({!r}).read_text() + ' (build test)')\n".format(
            sys.executable, str(version_path)
        )
    )
    splunk_exec.chmod(0o755)
    include_task = next(
        task for task in yaml.safe_load(TASK_FILE.with_name("main.yml").read_text())
        if task.get("include_tasks") == TASK_FILE.name
    )
    include_task["include_tasks"] = str(TASK_FILE)
    playbook = tmp_path / "playbook.yml"
    playbook.write_text(yaml.safe_dump([{
        "hosts": "localhost",
        "connection": "local",
        "gather_facts": False,
        "vars": {
            "ansible_python_interpreter": sys.executable,
            "ansible_become": False,
            "splunk": {
                "home": str(tmp_path), "exec": str(splunk_exec),
                "user": getpass.getuser(), "group": grp.getgrgid(os.getgid()).gr_name,
                "role": "splunk_standalone",
            },
        },
        "tasks": [include_task],
    }]))
    env = dict(os.environ, ANSIBLE_LOG_PATH=str(tmp_path / "ansible.log"),
               ANSIBLE_LOCAL_TEMP=str(tmp_path / "local-tmp"),
               ANSIBLE_REMOTE_TEMP=str(tmp_path / "remote-tmp"), ANSIBLE_NOCOLOR="1")
    for version, expected_flag, expected_changes in [
        ("10.8.9", "false", 0),
        ("10.9.0", "true", 1),
        ("10.9.0", "true", 0),
    ]:
        version_path.write_text(version)
        result = subprocess.run(
            [sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(playbook)],
            env=env, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "changed={}".format(expected_changes) in result.stdout
        config = configparser.ConfigParser()
        config.read(config_path)
        assert config.get("kvstore", "defaultKVStoreType") == "local"
        assert config.get("kvstore", "postgresMigrateOnStartup") == expected_flag
