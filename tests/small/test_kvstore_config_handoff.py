"""Explicit KVService policy, legacy isolation, and backend handoff coverage."""

import configparser
import getpass
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest import mock

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar


TASK_DIR = Path(__file__).resolve().parents[2] / "roles/splunk_common/tasks"


sys.path.append(str(Path(__file__).resolve().parents[2] / "inventory"))
import environ


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


def _installation_state_task():
    tasks = yaml.safe_load((TASK_DIR / "main.yml").read_text())
    return next(task for task in tasks
                if task.get("name") == "Capture KVService installation state before Splunk CLI calls")


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
    "directory,conf_file,desired,preserve_if_enabled",
    [
        ("/opt/splunk/etc/system/local", "server.conf",
         {"kvstore": {"kvserviceConnectionString": "https://kvservice"}}, True),
        ("/opt/splunk/etc/system/local/", "server.conf",
         {"kvstore": {"kvserviceConnectionString": "https://kvservice"}}, True),
        ("/opt//splunk/etc/./system/local/", "server.conf",
         {"kvstore": {"kvserviceConnectionString": "https://kvservice"}}, True),
        ("/opt/splunk/etc/system/local/../local", "server.conf",
         {"kvstore": {"kvserviceConnectionString": "https://kvservice"}}, True),
        ("/opt/splunk/etc/apps/custom/local", "server.conf",
         {"kvstore": {"kvserviceConnectionString": "https://kvservice"}}, False),
        ("/opt/splunk/etc/system/local", "inputs.conf",
         {"kvstore": {"kvserviceConnectionString": "https://kvservice"}}, False),
        ("/opt/splunk/etc/system/local", "server.conf",
         {"kvstore": {"kvserviceConnectionString": "   "}}, True),
        ("/opt/splunk/etc/system/local", "server.conf",
         {"kvstore": {"defaultKVStoreType": "local"}}, True),
        ("/opt/splunk/etc/system/local", "server.conf",
         {"kvstore": {"kvserviceConnectionString": "https://kvservice",
                      "defaultKVStoreType": "external"}}, True),
        ("/opt/splunk/etc/system/local", "server.conf", {}, True),
        ("/opt/splunk/etc/system/local", "server.conf", {"kvstore": None}, True),
    ],
)
def test_enabled_system_local_cleanup_preserves_backend_for_any_desired_settings(
    enabled, directory, conf_file, desired, preserve_if_enabled
):
    loader = DataLoader()
    reconcile = loader.load_from_file(str(TASK_DIR / "reconcile_config_map_values.yml"))[-1]
    remove = loader.load_from_file(str(TASK_DIR / "remove_config_map_stanza.yml"))[0]
    variables = {"conf_directory": directory, "conf_file": conf_file,
                 "conf_stanzas": desired, "splunk": {"home": "/opt/splunk"}}
    if enabled is not None:
        variables["splunk_kvservice_enabled"] = enabled
    preserve = enabled is True and preserve_if_enabled
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
    capture = _installation_state_task()
    assert _condition(loader, capture, variables) is (enabled is not None)
    includes = [task.get("include_tasks") for task in tasks]
    assert includes.index("update_etc.yml") < tasks.index(capture) < includes.index("stop_splunk.yml")
    assert includes.count("set_config_file.yml") == 1
    assert includes.index("set_config_file.yml") < tasks.index(policy) < includes.index("start_splunk.yml")


@pytest.mark.parametrize(
    "release,enabled,role,backend,expected_backend,expected_migration,indexer_external",
    [
        ("10.6.0", True, "splunk_standalone", "external", "local", "false", False),
        ("10.6.7.1", False, "splunk_standalone", "external", "local", "false", False),
        ("10.9.0", False, "splunk_standalone", "external", "external", "true", False),
        ("10.9.0", True, "splunk_standalone", "local", "local", "true", False),
        ("10.9.0", True, "splunk_standalone", "external", "external", "true", False),
        ("10.9.0", True, "splunk_standalone", None, "local", "true", False),
        ("10.9.0", True, "splunk_standalone", "", "local", "true", False),
        ("10.9.0", True, "splunk_standalone", "other", "local", "true", False),
        ("10.10.0", True, "splunk_standalone", "external", "external", "true", False),
        ("10.7.0", True, "splunk_standalone", "external", "external", "false", False),
        ("10.8.9", False, "splunk_standalone", "external", "external", "true", False),
        ("10.6.0", True, "splunk_indexer", "external", "local", "false", False),
        ("10.6.7.1", False, "splunk_indexer", "external", "local", "false", False),
        ("10.8.9", True, "splunk_indexer", "local", "local", "false", False),
        ("10.9.0", False, "splunk_indexer", "external", "external", "true", False),
        ("10.9.0", True, "splunk_indexer", "local", "external", "true", True),
        ("10.9.0.0", True, "splunk_indexer", None, "external", "true", True),
        ("10.10.0", True, "splunk_indexer", "external", "external", "true", True),
        ("11.0.0", True, "splunk_indexer", "external", "external", "true", True),
        ("10.9.0", True, "splunk_search_head", "local", "local", "true", False),
        ("10.9.0", True, "splunk_search_head_captain", "local", "local", "true", False),
        ("10.9.0", True, "splunk_cluster_master", "local", "local", "true", False),
        ("10.9.0", True, "splunk_deployer", "local", "local", "true", False),
    ],
)
def test_actual_explicit_policy_tasks(
    tmp_path, release, enabled, role, backend, expected_backend, expected_migration,
    indexer_external,
):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    server_conf = local / "server.conf"
    (home / "etc/splunk.version").write_text("VERSION=%s\nBUILD=test\n" % release)
    initial_migration = "false" if enabled else "true"
    contents = ("[kvstore]\npostgresMigrateOnStartup = %s\ndisabled = false\n"
                "forceLocalForInternalCollections = true\nshutDownMongo = false\n") % initial_migration
    if backend is not None:
        contents += "defaultKVStoreType = %s\n" % backend
    contents += "[unrelated]\ndefaultKVStoreType = external\npercent = 50%\n"
    server_conf.write_text(contents)
    variables = _variables(home)
    variables["splunk"]["role"] = role
    variables["splunk_kvservice_enabled"] = enabled
    _run_tasks(tmp_path, variables, [
        _main_include("set_default_kvstore_type.yml"),
        _main_include("set_kvservice_startup_policy.yml"),
    ])
    conf = configparser.ConfigParser()
    conf.read(server_conf)
    assert conf["kvstore"].get("defaultKVStoreType") == expected_backend
    assert conf["kvstore"]["postgresMigrateOnStartup"] == expected_migration
    assert conf["kvstore"]["disabled"] == ("true" if role == "splunk_indexer" else "false")
    assert conf["kvstore"]["forceLocalForInternalCollections"] == ("false" if indexer_external else "true")
    assert conf["kvstore"]["shutDownMongo"] == ("true" if indexer_external else "false")


@pytest.mark.parametrize(
    "release,enabled,fresh,backend,expected_backend,expected_migration,role",
    [
        ("10.9.0", True, True, "local", "external", "true", "splunk_standalone"),
        ("10.9.0", True, False, "local", "local", "true", "splunk_standalone"),
        ("10.9.0", True, False, "external", "external", "true", "splunk_standalone"),
        ("10.9.0", True, False, None, "local", "true", "splunk_standalone"),
        ("10.9.0", True, False, "other", "local", "true", "splunk_standalone"),
        ("10.10.0", True, True, None, "external", "true", "splunk_search_head"),
        ("10.6.0", True, True, None, "local", "false", "splunk_standalone"),
        ("10.8.0", True, True, "local", "local", "false", "splunk_standalone"),
        ("10.9.0", False, True, "external", "local", "false", "splunk_standalone"),
        ("10.9.0", True, True, "local", "external", "true", "splunk_indexer"),
    ],
)
def test_actual_initialization_uses_state_captured_before_early_cli(
    tmp_path, release, enabled, fresh, backend, expected_backend, expected_migration, role
):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    marker = home / "etc/myinstall/splunkd.xml"
    marker.parent.mkdir()
    if not fresh:
        marker.touch()
    if fresh:
        secret = home / "etc/auth/splunk.secret"
        secret.parent.mkdir()
        secret.write_text("preseeded-secret")
    (home / "etc/splunk.version").write_text("VERSION=%s\nBUILD=test\n" % release)
    contents = ("[kvstore]\npostgresMigrateOnStartup = false\n"
                "forceLocalForInternalCollections = true\nshutDownMongo = false\n")
    if backend is not None:
        contents += "defaultKVStoreType = %s\n" % backend
    server_conf = local / "server.conf"
    server_conf.write_text(contents)
    fake_cli = tmp_path / "splunk-version"
    fake_cli.write_text("#!%s\nfrom pathlib import Path\nPath(%r).touch()\n" % (sys.executable, str(marker)))
    fake_cli.chmod(0o755)
    desired = {"kvstore": {"kvserviceConnectionString": "https://kvservice"}} if enabled else {
        "kvstore": {"defaultKVStoreType": "local", "postgresMigrateOnStartup": "false"},
    }
    variables = _variables(home)
    variables["splunk"].update({"role": role, "exec": str(fake_cli),
                                "conf": {"server": {"content": desired}}})
    variables.update({"splunk_kvservice_enabled": enabled, "first_run": not fresh})
    _run_tasks(tmp_path, variables, [
        _installation_state_task(),
        {"command": "{{ splunk.exec }} version"},
        _main_include("set_config_file.yml"),
        _main_include("set_kvservice_startup_policy.yml"),
        # A subsequent reconciliation sees the native marker created by the CLI.
        _installation_state_task(),
        _main_include("set_config_file.yml"),
        _main_include("set_kvservice_startup_policy.yml"),
    ])
    conf = configparser.ConfigParser()
    conf.read(server_conf)
    assert conf["kvstore"]["defaultKVStoreType"] == expected_backend
    assert conf["kvstore"]["postgresMigrateOnStartup"] == expected_migration
    external_initialization = enabled and release.startswith(("10.9.", "10.10.")) and fresh
    assert conf["kvstore"]["forceLocalForInternalCollections"] == ("false" if external_initialization else "true")
    assert conf["kvstore"]["shutDownMongo"] == ("true" if external_initialization else "false")
    assert conf["kvstore"].get("disabled") == ("true" if role == "splunk_indexer" else None)


@pytest.mark.parametrize("release", ["10.6.0", "10.9.0", "10.10.0"])
@pytest.mark.parametrize("role", ["splunk_standalone", "splunk_indexer"])
def test_actual_disabled_config_render_restores_local_policy_after_cleanup(tmp_path, release, role):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    server_conf = local / "server.conf"
    (home / "etc/splunk.version").write_text("VERSION=%s\nBUILD=test\n" % release)
    previous = {"kvstore": {
        "defaultKVStoreType": "external", "postgresMigrateOnStartup": "true",
        "kvserviceConnectionString": "https://old-kvservice",
    }}
    server_conf.write_text(
        "[kvstore]\ndefaultKVStoreType = external\npostgresMigrateOnStartup = true\n"
        "kvserviceConnectionString = https://old-kvservice\n[general]\nserverName = keep-me\n"
    )
    managed = local / ".server.conf.splunk-ansible-managed.yml"
    managed.write_text(yaml.safe_dump(previous))
    desired = {"kvstore": {"defaultKVStoreType": "local", "postgresMigrateOnStartup": "false"}}
    variables = _variables(home)
    variables["splunk"]["role"] = role
    variables["splunk"]["conf"] = {"server": {"content": desired}}
    variables["splunk_kvservice_enabled"] = False
    # Exercise the real main.yml rendering include, cleanup, and repeated reconciliation.
    _run_tasks(tmp_path, variables, [
        _main_include("set_default_kvstore_type.yml"),
        _main_include("set_config_file.yml"),
        _main_include("set_kvservice_startup_policy.yml"),
        _main_include("set_config_file.yml"),
        _main_include("set_kvservice_startup_policy.yml"),
    ])
    conf = configparser.ConfigParser()
    conf.read(server_conf)
    expected = {"defaultkvstoretype": "local", "postgresmigrateonstartup": "false"}
    if role == "splunk_indexer":
        expected["disabled"] = "true"
    assert dict(conf["kvstore"]) == expected
    assert conf["general"]["serverName"] == "keep-me"
    assert yaml.safe_load(managed.read_text()) == desired


@pytest.mark.parametrize("enabled", [None, False, True])
def test_actual_legacy_endpoint_cleanup_requires_explicit_disabled_input(tmp_path, enabled):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    server_conf = local / "server.conf"
    contents = ("[kvstore]\nkvserviceConnectionString = https://saved-kvservice\n"
                "defaultKVStoreType = local\n[general]\nserverName = keep-me\n")
    server_conf.write_text(contents)
    variables = _variables(home)
    if enabled is not None:
        variables["splunk_kvservice_enabled"] = enabled
    _run_tasks(tmp_path, variables, [
        _main_include("remove_legacy_kvservice_connection_string.yml"),
    ])
    if enabled is not False:
        assert server_conf.read_text() == contents
    else:
        conf = configparser.ConfigParser()
        conf.read(server_conf)
        assert "kvserviceConnectionString" not in conf["kvstore"]
        assert conf["kvstore"]["defaultKVStoreType"] == "local"
        assert conf["general"]["serverName"] == "keep-me"


@pytest.mark.parametrize("enabled", [False, True])
def test_actual_sok_connection_and_scs_settings_use_normal_rendering(tmp_path, enabled):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    server_conf = local / "server.conf"
    server_conf.write_text("[kvstore]\nkvserviceConnectionString = https://legacy-kvservice\n")
    (home / "etc/splunk.version").write_text("VERSION=10.9.0\nBUILD=test\n")
    desired = {
        "kvstore": {"kvserviceConnectionString": "https://sok-kvservice"},
        "scs": {"tenant": "sok-tenant", "mvl-enabled": "true"},
    } if enabled else {
        "kvstore": {"defaultKVStoreType": "local", "postgresMigrateOnStartup": "false"},
    }
    variables = _variables(home)
    variables["splunk"]["conf"] = [{"key": "server", "value": {"content": desired}}]
    variables["splunk_kvservice_enabled"] = enabled
    _run_tasks(tmp_path, variables, [
        _main_include("remove_legacy_kvservice_connection_string.yml"),
        _main_include("set_config_file.yml"),
        _main_include("set_kvservice_startup_policy.yml"),
        _main_include("remove_legacy_kvservice_connection_string.yml"),
        _main_include("set_config_file.yml"),
        _main_include("set_kvservice_startup_policy.yml"),
    ])
    conf = configparser.ConfigParser()
    conf.read(server_conf)
    assert conf["kvstore"].get("kvserviceConnectionString") == (
        "https://sok-kvservice" if enabled else None
    )
    assert "kvserviceScope" not in conf["kvstore"]
    if enabled:
        assert dict(conf["scs"]) == {"tenant": "sok-tenant", "mvl-enabled": "true"}
    else:
        assert conf["kvstore"]["defaultKVStoreType"] == "local"
        assert conf["kvstore"]["postgresMigrateOnStartup"] == "false"
        assert "scs" not in conf


@pytest.mark.parametrize("saved_backend", ["external", "local"])
@pytest.mark.parametrize("directory_alias", [False, True], ids=["implicit-directory", "aliased-directory"])
def test_actual_multi_entry_sok_handoff_preserves_backend(tmp_path, saved_backend, directory_alias):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    server_conf = local / "server.conf"
    server_conf.write_text(
        "[kvstore]\ndefaultKVStoreType = %s\n"
        "kvserviceConnectionString = https://old-kvservice\n"
        "[general]\nserverName = old-name\n" % saved_backend
    )
    (home / "etc/splunk.version").write_text("VERSION=10.9.0\nBUILD=test\n")
    marker = home / "etc/myinstall/splunkd.xml"
    marker.parent.mkdir()
    marker.write_text("<splunk/>\n")
    managed = local / ".server.conf.splunk-ansible-managed.yml"
    managed.write_text(yaml.safe_dump({
        "kvstore": {"defaultKVStoreType": "local",
                    "kvserviceConnectionString": "https://old-kvservice"},
        "general": {"serverName": "old-name"},
    }))
    variables = environ.merge_dict(environ.loadBaseDefaults(), _variables(home))
    variables["splunk"].update({"conf": [
        {"key": "server", "value": {"content": {"general": {"serverName": "customer-name"}}}},
    ]})
    if directory_alias:
        variables["splunk"]["conf"][0]["value"]["directory"] = str(home) + "/etc//./system/local/"
    sok_settings = {
        "kvstore": {"kvserviceConnectionString": "https://new-kvservice"},
        "scs": {"tenant": "sok-tenant", "mvl-enabled": "true"},
    }
    environ.merge_dict(variables, {"splunk": {"conf": [
        {"key": "server", "value": {"content": sok_settings}},
    ]}})
    with mock.patch.dict(os.environ, {
        "SPLUNK_KVSERVICE_ENABLED": "true", "SPLUNK_NOAH_ENABLED": "false",
    }, clear=True), mock.patch.object(environ, "loadDefaults", return_value=variables), \
            mock.patch.object(environ, "getSecrets"), mock.patch.object(environ, "getHEC"):
        variables = environ.getDefaultVars()
    _run_tasks(tmp_path, variables, [
        _installation_state_task(),
        _main_include("set_config_file.yml"),
        _main_include("set_kvservice_startup_policy.yml"),
        _main_include("set_config_file.yml"),
        _main_include("set_kvservice_startup_policy.yml"),
    ])
    conf = configparser.ConfigParser()
    conf.read(server_conf)
    assert conf["kvstore"]["defaultKVStoreType"] == saved_backend
    assert conf["kvstore"]["kvserviceConnectionString"] == "https://new-kvservice"
    assert conf["kvstore"]["postgresMigrateOnStartup"] == "true"
    assert conf["general"]["serverName"] == "customer-name"
    assert dict(conf["scs"]) == {"tenant": "sok-tenant", "mvl-enabled": "true"}
    assert yaml.safe_load(managed.read_text()) == {
        "general": {"serverName": "customer-name"}, **sok_settings,
    }


@pytest.mark.parametrize("requested_type", ["local", "cohosted", "external"])
@pytest.mark.parametrize("role", ["splunk_standalone", "splunk_indexer"])
def test_actual_unset_input_keeps_legacy_type_and_startup_behavior(tmp_path, requested_type, role):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    fake_cli = tmp_path / "splunk-version"
    fake_cli.write_text("#!/bin/sh\nprintf '%s\\n' 'Splunk 10.9.0 (test)'\n")
    fake_cli.chmod(0o755)
    variables = _variables(home)
    variables["splunk"]["role"] = role
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
    assert conf["kvstore"]["postgresMigrateOnStartup"] == (
        "false" if requested_type == "local" else "true"
    )
    for option in ("disabled", "forceLocalForInternalCollections", "shutDownMongo"):
        assert option not in conf["kvstore"]


@pytest.mark.parametrize("saved_backend", ["local", "external"])
@pytest.mark.parametrize("enabled", [None, False, True])
@pytest.mark.parametrize("desired", [
    {"kvstore": {"kvserviceConnectionString": "https://kvservice"}},
    {"general": {"serverName": "customer-name"}},
    {"kvstore": {"defaultKVStoreType": "local"}},
])
def test_actual_handoff_preserves_backend_only_with_explicit_enabled_input(
    tmp_path, saved_backend, enabled, desired
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
    _run_tasks(tmp_path, variables, [
        _include("set_config_file.yml", vars={"conf_stanzas": desired}),
        _include("set_config_file.yml", vars={"conf_stanzas": desired}),
    ])
    conf = configparser.ConfigParser()
    conf.read(server_conf)
    expected_backend = desired.get("kvstore", {}).get(
        "defaultKVStoreType", saved_backend if enabled is True else None,
    )
    assert conf["kvstore"].get("defaultKVStoreType") == expected_backend
    assert "postgresMigrateOnStartup" not in conf["kvstore"]
    assert conf["kvstore"].get("kvserviceConnectionString") == desired.get("kvstore", {}).get(
        "kvserviceConnectionString",
    )
    if "general" in desired:
        assert conf["general"]["serverName"] == "customer-name"
    assert yaml.safe_load(managed.read_text()) == desired
