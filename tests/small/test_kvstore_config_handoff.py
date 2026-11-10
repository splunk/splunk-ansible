"""Explicit KVService policy, legacy isolation, and backend handoff coverage."""

import configparser
import getpass
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar


TASK_DIR = Path(__file__).resolve().parents[2] / "roles/splunk_common/tasks"


def _run_tasks(tmp_path, variables, tasks):
    playbook_bin = shutil.which("ansible-playbook")
    assert playbook_bin, "Ansible is required to exercise the configuration tasks"
    playbook = tmp_path / "verify-kvstore.yml"
    playbook.write_text(yaml.safe_dump([{
        "hosts": "localhost", "gather_facts": False,
        "vars": variables, "tasks": tasks,
    }]))
    ansible_config = tmp_path / "ansible.cfg"
    ansible_config.write_text("[defaults]\nhash_behaviour=merge\n")
    env = dict(os.environ, ANSIBLE_CONFIG=str(ansible_config),
               ANSIBLE_LOCAL_TEMP=str(tmp_path / "ansible-local"),
               ANSIBLE_REMOTE_TEMP=str(tmp_path / "ansible-remote"),
               ANSIBLE_LOG_PATH=str(tmp_path / "ansible.log"), ANSIBLE_NOCOLOR="1")
    result = subprocess.run(
        [playbook_bin, "-i", "localhost,", "-c", "local", str(playbook)],
        env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=180, check=False,
    )
    assert result.returncode == 0, result.stdout


def _include(task_file, **extra):
    return {"include_tasks": str(TASK_DIR / task_file), **extra}


def _main_include(task_file):
    tasks = yaml.safe_load((TASK_DIR / "main.yml").read_text())
    task = next(task for task in tasks if task.get("include_tasks") == task_file)
    task["include_tasks"] = str(TASK_DIR / task_file)
    return task


def _variables(home):
    return {
        "splunk": {"home": str(home), "exec": "/must-not-call-splunk-cli",
                   "role": "splunk_standalone", "user": getpass.getuser(),
                   "group": str(os.getgid()), "kvstore": {"default_kvstore_type": "external"}},
        "hide_password": False,
        "ansible_python_interpreter": sys.executable,
    }


def _condition(loader, task, variables):
    condition = Conditional(loader=loader)
    when = task["when"]
    condition.when = when if isinstance(when, list) else [when]
    return condition.evaluate_conditional(Templar(loader=loader, variables=variables), variables)


@pytest.mark.parametrize("enabled", [None, False, True])
@pytest.mark.parametrize(
    "directory,conf_file,desired,enabled_handoff",
    [
        ("/opt/splunk/etc/system/local", "server.conf",
         {"kvstore": {"kvserviceConnectionString": "https://kvservice"}}, True),
        ("/opt/splunk/etc/system/local/", "server.conf",
         {"kvstore": {"kvserviceConnectionString": "https://kvservice"}}, True),
        ("/opt/splunk/etc/apps/custom/local", "server.conf",
         {"kvstore": {"kvserviceConnectionString": "https://kvservice"}}, False),
        ("/opt/splunk/etc/system/local", "inputs.conf",
         {"kvstore": {"kvserviceConnectionString": "https://kvservice"}}, False),
        ("/opt/splunk/etc/system/local", "server.conf",
         {"kvstore": {"kvserviceConnectionString": "   "}}, False),
        ("/opt/splunk/etc/system/local", "server.conf",
         {"kvstore": {"defaultKVStoreType": "local"}}, False),
        ("/opt/splunk/etc/system/local", "server.conf",
         {"kvstore": {"kvserviceConnectionString": "https://kvservice",
                      "defaultKVStoreType": "external"}}, False),
        ("/opt/splunk/etc/system/local", "server.conf", {}, False),
        ("/opt/splunk/etc/system/local", "server.conf", {"kvstore": None}, False),
    ],
)
def test_only_explicit_enabled_system_local_handoff_preserves_backend(
    enabled, directory, conf_file, desired, enabled_handoff
):
    loader = DataLoader()
    reconcile = loader.load_from_file(str(TASK_DIR / "reconcile_config_map_values.yml"))[-1]
    remove = loader.load_from_file(str(TASK_DIR / "remove_config_map_stanza.yml"))[0]
    variables = {"conf_directory": directory, "conf_file": conf_file,
                 "conf_stanzas": desired, "splunk": {"home": "/opt/splunk"}}
    if enabled is not None:
        variables["splunk_kvservice_enabled"] = enabled
    preserve = enabled is True and enabled_handoff
    variables["config_map_preserve_kvstore_backend"] = Templar(
        loader=loader, variables=variables
    ).template(reconcile["vars"]["config_map_preserve_kvstore_backend"])
    assert variables["config_map_preserve_kvstore_backend"] is preserve
    for stanza, option in [("kvstore", "defaultKVStoreType"),
                           ("kvstore", "kvserviceConnectionString"),
                           ("kvstore", "postgresMigrateOnStartup"),
                           ("general", "defaultKVStoreType")]:
        variables.update({"config_map_stanza_name": stanza,
                          "config_map_stanza_settings": {option: "previous"},
                          "config_map_stanza_setting": {"key": option, "value": "previous"}})
        assert _condition(loader, remove, variables) is not (
            preserve and stanza == "kvstore" and option == "defaultKVStoreType"
        )


@pytest.mark.parametrize("enabled", [None, False, True])
def test_new_policy_requires_explicit_input_and_runs_after_render(enabled):
    loader = DataLoader()
    tasks = loader.load_from_file(str(TASK_DIR / "main.yml"))
    policy = next(task for task in tasks
                  if task.get("include_tasks") == "set_kvservice_startup_policy.yml")
    variables = {"splunk": {"role": "splunk_standalone"}}
    if enabled is not None:
        variables["splunk_kvservice_enabled"] = enabled
    assert _condition(loader, policy, variables) is (enabled is not None)
    includes = [task.get("include_tasks") for task in tasks]
    assert includes.count("set_config_file.yml") == 1
    assert includes.index("set_config_file.yml") < tasks.index(policy) < includes.index("start_splunk.yml")


@pytest.mark.parametrize(
    "release,enabled,backend,expected_backend,expected_migration",
    [
        ("10.6.0", True, "external", "local", "false"),
        ("10.6.7.1", False, "external", "local", "false"),
        ("10.9.0", False, "external", "local", "false"),
        ("10.9.0", True, "local", "local", "true"),
        ("10.9.0", True, "external", "external", "true"),
        ("10.9.0", True, None, None, "true"),
        ("10.10.0", True, "external", "external", "true"),
        ("10.7.0", True, "external", "external", "false"),
        ("10.8.9", False, "external", "external", "false"),
    ],
)
def test_actual_explicit_policy_tasks(
    tmp_path, release, enabled, backend, expected_backend, expected_migration
):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    server_conf = local / "server.conf"
    (home / "etc/splunk.version").write_text("VERSION=%s\nBUILD=test\n" % release)
    contents = "[kvstore]\npostgresMigrateOnStartup = false\n"
    if backend is not None:
        contents += "defaultKVStoreType = %s\n" % backend
    server_conf.write_text(contents)
    variables = _variables(home)
    variables["splunk_kvservice_enabled"] = enabled
    _run_tasks(tmp_path, variables, [
        _main_include("set_default_kvstore_type.yml"),
        _main_include("set_kvservice_startup_policy.yml"),
    ])
    conf = configparser.ConfigParser()
    conf.read(server_conf)
    assert conf["kvstore"].get("defaultKVStoreType") == expected_backend
    assert conf["kvstore"]["postgresMigrateOnStartup"] == expected_migration


@pytest.mark.parametrize("requested_type", ["cohosted", "external"])
def test_actual_unset_input_keeps_legacy_type_and_startup_behavior(tmp_path, requested_type):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    fake_cli = tmp_path / "splunk-version"
    fake_cli.write_text("#!/bin/sh\nprintf '%s\\n' 'Splunk 10.6.0 (test)'\n")
    fake_cli.chmod(0o755)
    variables = _variables(home)
    variables["splunk"]["exec"] = str(fake_cli)
    variables["splunk"]["kvstore"]["default_kvstore_type"] = requested_type
    # No splunk.version file: entering the new policy would fail this legacy test.
    _run_tasks(tmp_path, variables, [
        _main_include("set_default_kvstore_type.yml"),
        _main_include("set_kvservice_startup_policy.yml"),
    ])
    conf = configparser.ConfigParser()
    conf.read(local / "server.conf")
    assert conf["kvstore"]["defaultKVStoreType"] == requested_type
    assert conf["kvstore"]["postgresMigrateOnStartup"] == "true"


@pytest.mark.parametrize("saved_backend", ["local", "external"])
@pytest.mark.parametrize("enabled", [None, True])
def test_actual_handoff_preserves_backend_only_with_explicit_enabled_input(
    tmp_path, saved_backend, enabled
):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    server_conf = local / "server.conf"
    server_conf.write_text("[kvstore]\ndefaultKVStoreType = %s\npostgresMigrateOnStartup = false\n" % saved_backend)
    managed = local / ".server.conf.splunk-ansible-managed.yml"
    managed.write_text(yaml.safe_dump({"kvstore": {
        "defaultKVStoreType": "local", "postgresMigrateOnStartup": "false",
        "kvserviceConnectionString": "https://old-kvservice",
    }}))
    variables = _variables(home)
    variables.update({"conf_directory": str(local), "conf_file": "server.conf",
                      "reconcile_config_map_values": True})
    if enabled is not None:
        variables["splunk_kvservice_enabled"] = enabled
    desired = {"kvstore": {"kvserviceConnectionString": "https://kvservice"}}
    _run_tasks(tmp_path, variables, [
        _include("set_config_file.yml", vars={"conf_stanzas": desired}),
        _include("set_config_file.yml", vars={"conf_stanzas": desired}),
    ])
    conf = configparser.ConfigParser()
    conf.read(server_conf)
    assert conf["kvstore"].get("defaultKVStoreType") == (saved_backend if enabled is True else None)
    assert "postgresMigrateOnStartup" not in conf["kvstore"]
    assert conf["kvstore"]["kvserviceConnectionString"] == "https://kvservice"
    assert yaml.safe_load(managed.read_text()) == desired
