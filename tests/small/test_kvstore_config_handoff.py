"""Explicit KVService policy, legacy isolation, and backend handoff coverage."""

import configparser
import getpass
import os
from pathlib import Path
import shlex
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


def _indexer_policy_task():
    tasks = yaml.safe_load((TASK_DIR / "main.yml").read_text())
    return next(task for task in tasks if task.get("name") == "Keep KV Store disabled on indexers")


def _installed_release_task():
    tasks = yaml.safe_load((TASK_DIR / "main.yml").read_text())
    return next(task for task in tasks
                if task.get("name") == "Read the installed release for KV Store settings")


def _policy_tasks():
    return [_installed_release_task(), _main_include("set_default_kvstore_type.yml"),
            _indexer_policy_task(), _main_include("set_kvservice_startup_policy.yml")]


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
    "stanza,option",
    [
        ("kvstore", "defaultKVStoreType"),
        ("kvstore", "kvserviceConnectionString"),
        ("kvstore", "postgresMigrateOnStartup"),
        ("general", "defaultKVStoreType"),
    ],
)
def test_cleanup_preserves_only_kvstore_backend_when_enabled(enabled, stanza, option):
    loader = DataLoader()
    remove = loader.load_from_file(str(TASK_DIR / "remove_config_map_stanza.yml"))[0]
    variables = {
        "config_map_stanza_name": stanza,
        "config_map_stanza_settings": {option: "previous"},
        "config_map_stanza_setting": {"key": option, "value": "previous"},
    }
    if enabled is not None:
        variables["splunk_kvservice_enabled"] = enabled
    preserve = enabled is True and stanza == "kvstore" and option == "defaultKVStoreType"
    assert _condition(loader, remove, variables) is not preserve


@pytest.mark.parametrize("enabled", [None, False, True])
@pytest.mark.parametrize("role", ["splunk_standalone", "splunk_indexer"])
@pytest.mark.parametrize("release", ["10.6.7.1", "10.8.9", "10.9.0", "10.10.0"])
def test_version_selects_setter_after_render(enabled, role, release):
    loader = DataLoader()
    tasks = loader.load_from_file(str(TASK_DIR / "main.yml"))
    policy = next(task for task in tasks
                  if task.get("include_tasks") == "set_kvservice_startup_policy.yml")
    variables = {"splunk": {"role": role, "kvstore": {"default_kvstore_type": "local"}},
                 "kvservice_installed_release": release}
    if enabled is not None:
        variables["splunk_kvservice_enabled"] = enabled
    assert _condition(loader, policy, variables) is (
        enabled is not None and release.startswith(("10.9.", "10.10."))
    )
    capture = _installation_state_task()
    assert _condition(loader, capture, variables) is (enabled is not None)
    includes = [task.get("include_tasks") for task in tasks]
    assert includes.index("update_etc.yml") < tasks.index(capture) < includes.index("stop_splunk.yml")
    assert tasks.index(capture) < includes.index("set_default_kvstore_type.yml")
    assert includes.count("set_config_file.yml") == 1
    assert includes.index("set_config_file.yml") < tasks.index(policy) < includes.index("start_splunk.yml")
    indexer_policy = _indexer_policy_task()
    assert _condition(loader, indexer_policy, variables) is (enabled is not None and role == "splunk_indexer")
    assert includes.count("set_default_kvstore_type.yml") == 1
    legacy = next(task for task in tasks if task.get("include_tasks") == "set_default_kvstore_type.yml")
    assert _condition(loader, legacy, variables) is release.startswith("10.6.")
    assert (includes.index("set_config_file.yml") < tasks.index(_installed_release_task())
            < tasks.index(legacy)
            < tasks.index(indexer_policy) < tasks.index(policy))


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("role", ["splunk_standalone", "splunk_indexer"])
def test_new_setter_leaves_10_6_configuration_unchanged(tmp_path, enabled, role):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    server_conf = local / "server.conf"
    contents = "[kvstore]\ndefaultKVStoreType = external\npostgresMigrateOnStartup = true\ndisabled = false\n"
    server_conf.write_text(contents)
    (home / "etc/splunk.version").write_text("VERSION=10.6.7.1\nBUILD=test\n")
    variables = _variables(home)
    variables["splunk"].update({"role": role})
    variables["splunk_kvservice_enabled"] = enabled
    _run_tasks(tmp_path, variables, [
        _installed_release_task(), _main_include("set_kvservice_startup_policy.yml"),
    ])
    assert server_conf.read_text() == contents


def test_actual_universal_forwarder_skips_version_read_and_both_setters(tmp_path):
    home = tmp_path / "splunk"
    variables = _variables(home)
    variables["splunk"]["role"] = "splunk_universal_forwarder"
    variables["splunk_kvservice_enabled"] = True
    _run_tasks(tmp_path, variables, _policy_tasks())
    assert not home.exists()


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
    variables["splunk"]["kvstore"]["default_kvstore_type"] = "local"
    fake_cli = tmp_path / "splunk-version"
    fake_cli.write_text(
        "#!/bin/sh\nprintf '%s\\n' 'Splunk {} (test)'\n".format(release)
        if release.startswith("10.6.") else "#!/bin/sh\nexit 99\n"
    )
    fake_cli.chmod(0o755)
    variables["splunk"]["exec"] = str(fake_cli)
    _run_tasks(tmp_path, variables, _policy_tasks())
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
    fake_cli.write_text("#!%s\nfrom pathlib import Path\nPath(%r).touch()\nprint(%r)\n" % (
        sys.executable, str(marker), "Splunk {} (test)".format(release),
    ))
    fake_cli.chmod(0o755)
    desired = {"kvstore": {"kvserviceConnectionString": "https://kvservice"}} if enabled else {
        "kvstore": {"defaultKVStoreType": "local", "postgresMigrateOnStartup": "false"},
    }
    variables = _variables(home)
    variables["splunk"]["kvstore"]["default_kvstore_type"] = "local"
    variables["splunk"].update({"role": role, "exec": str(fake_cli),
                                "conf": {"server": {"content": desired}}})
    variables.update({"splunk_kvservice_enabled": enabled, "first_run": not fresh})
    _run_tasks(tmp_path, variables, [
        _installation_state_task(),
        {"command": "{{ splunk.exec }} version"},
        _main_include("set_config_file.yml"),
        *_policy_tasks(),
        # A subsequent reconciliation sees the native marker created by the CLI.
        _installation_state_task(),
        _main_include("set_config_file.yml"),
        *_policy_tasks(),
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
    variables["splunk"]["kvstore"]["default_kvstore_type"] = "local"
    fake_cli = tmp_path / "splunk-version"
    fake_cli.write_text("#!/bin/sh\nprintf '%s\\n' 'Splunk {} (test)'\n".format(release))
    fake_cli.chmod(0o755)
    variables["splunk"]["exec"] = str(fake_cli)
    # Exercise the real main.yml rendering include, cleanup, and repeated reconciliation.
    _run_tasks(tmp_path, variables, [
        _main_include("set_config_file.yml"),
        *_policy_tasks(),
        _main_include("set_config_file.yml"),
        *_policy_tasks(),
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
        *_policy_tasks(),
        _main_include("remove_legacy_kvservice_connection_string.yml"),
        _main_include("set_config_file.yml"),
        *_policy_tasks(),
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
        *_policy_tasks(),
        _main_include("set_config_file.yml"),
        *_policy_tasks(),
    ])
    conf = configparser.ConfigParser()
    conf.read(server_conf)
    assert conf["kvstore"]["defaultKVStoreType"] == saved_backend
    assert conf["kvstore"]["kvserviceConnectionString"] == "https://new-kvservice"
    assert conf["kvstore"]["postgresMigrateOnStartup"] == "true"
    assert dict(conf["scs"]) == {"tenant": "sok-tenant", "mvl-enabled": "true"}
    assert yaml.safe_load(managed.read_text()) == sok_settings


@pytest.mark.parametrize(
    "release,enabled,saved_backend,fresh,expected_backend,expected_migration",
    [
        ("10.6.0", None, "external", False, "local", "false"),
        ("10.6.7.1", True, "external", False, "local", "false"),
        ("10.6.0", False, "external", False, "local", "false"),
        ("10.9.0", True, "external", False, "external", "true"),
        ("10.9.0", True, "local", False, "local", "true"),
        ("10.9.0", True, "local", True, "external", "true"),
        ("10.9.0", False, "local", False, "local", "false"),
    ],
)
def test_actual_legacy_local_input_preserves_version_policy(
    tmp_path, release, enabled, saved_backend, fresh, expected_backend, expected_migration
):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    server_conf = local / "server.conf"
    server_conf.write_text(
        "[kvstore]\ndefaultKVStoreType = %s\npostgresMigrateOnStartup = false\n"
        "[unrelated]\nsetting = keep-me\n" % saved_backend
    )
    (home / "etc/splunk.version").write_text("VERSION=%s\nBUILD=test\n" % release)
    (local / ".server.conf.splunk-ansible-managed.yml").write_text(yaml.safe_dump({
        "kvstore": {"defaultKVStoreType": "local", "postgresMigrateOnStartup": "false"},
    }))
    marker = home / "etc/myinstall/splunkd.xml"
    marker.parent.mkdir()
    if not fresh:
        marker.write_text("<splunk/>\n")
    fake_cli = tmp_path / "splunk-version"
    fake_cli.write_text("#!/bin/sh\ntouch {}\nprintf '%s\\n' 'Splunk {} (test)'\n".format(
        shlex.quote(str(marker)), release,
    ))
    fake_cli.chmod(0o755)
    variables = _variables(home)
    variables["splunk"]["exec"] = str(fake_cli)
    environment = {"SPLUNK_KVSTORE_DEFAULT_TYPE": "local"}
    if enabled is not None:
        environment["SPLUNK_KVSERVICE_ENABLED"] = str(enabled).lower()
    with mock.patch.dict(os.environ, environment, clear=True):
        environ.getDefaultKVStoreType(variables)
        environ.getKVServiceEnabled(variables)
    desired = {"kvstore": {"kvserviceConnectionString": "https://kvservice"}} if enabled else {
        "kvstore": {"defaultKVStoreType": "local", "postgresMigrateOnStartup": "false"},
    }
    variables["splunk"]["conf"] = (
        [{"key": "server", "value": {"content": desired}}] if enabled is not None else {
            "server": {"content": {"kvstore": {
                "defaultKVStoreType": "external", "postgresMigrateOnStartup": "true",
            }}},
        }
    )
    _run_tasks(tmp_path, variables, [
        _installation_state_task(), {"command": "{{ splunk.exec }} version"},
    ] + [
        task
        for _ in range(2)
        for task in (_main_include("set_config_file.yml"), *_policy_tasks())
    ])
    conf = configparser.ConfigParser()
    conf.read(server_conf)
    assert conf["kvstore"]["defaultKVStoreType"] == expected_backend
    assert conf["kvstore"]["postgresMigrateOnStartup"] == expected_migration
    assert conf["unrelated"]["setting"] == "keep-me"
    assert marker.exists()


@pytest.mark.parametrize("requested_type", ["local", "cohosted", "external"])
@pytest.mark.parametrize("role", ["splunk_standalone", "splunk_indexer"])
def test_actual_unset_input_keeps_legacy_type_and_startup_behavior(tmp_path, requested_type, role):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    (home / "etc/splunk.version").write_text("VERSION=10.6.7.1\nBUILD=test\n")
    fake_cli = tmp_path / "splunk-version"
    fake_cli.write_text("#!/bin/sh\nprintf '%s\\n' 'Splunk 10.6.7.1 (test)'\n")
    fake_cli.chmod(0o755)
    variables = _variables(home)
    variables["splunk"]["role"] = role
    variables["splunk"]["exec"] = str(fake_cli)
    variables["splunk"]["kvstore"]["default_kvstore_type"] = requested_type
    _run_tasks(tmp_path, variables, [
        _main_include("set_config_file.yml"),
        *_policy_tasks(),
    ])
    conf = configparser.ConfigParser()
    conf.read(local / "server.conf")
    assert conf["kvstore"]["defaultKVStoreType"] == requested_type
    assert conf["kvstore"]["postgresMigrateOnStartup"] == (
        "false" if requested_type == "local" else "true"
    )
    for option in ("disabled", "forceLocalForInternalCollections", "shutDownMongo"):
        assert option not in conf["kvstore"]


def test_actual_10_9_unset_input_leaves_custom_configuration_in_control(tmp_path):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    server_conf = local / "server.conf"
    server_conf.write_text("[kvstore]\ndefaultKVStoreType = external\npostgresMigrateOnStartup = true\n")
    (home / "etc/splunk.version").write_text("VERSION=10.9.0\nBUILD=test\n")
    variables = _variables(home)
    variables["splunk"]["kvstore"]["default_kvstore_type"] = "local"
    variables["splunk"]["conf"] = {"server": {"content": {
        "kvstore": {"postgresMigrateOnStartup": "false"},
    }}}
    _run_tasks(tmp_path, variables, [
        _main_include("set_config_file.yml"), *_policy_tasks(),
    ])
    conf = configparser.ConfigParser()
    conf.read(server_conf)
    assert conf["kvstore"]["defaultKVStoreType"] == "external"
    assert conf["kvstore"]["postgresMigrateOnStartup"] == "false"


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
