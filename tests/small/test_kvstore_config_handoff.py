"""KVService configuration ownership and version-policy task coverage."""

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


@pytest.mark.parametrize(
    "directory,conf_file,desired,preserve",
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
def test_only_enabled_system_local_handoff_preserves_backend(
    directory, conf_file, desired, preserve
):
    loader = DataLoader()
    reconcile = loader.load_from_file(str(TASK_DIR / "reconcile_config_map_values.yml"))[-1]
    remove = loader.load_from_file(str(TASK_DIR / "remove_config_map_stanza.yml"))[0]
    variables = {
        "conf_directory": directory,
        "conf_file": conf_file,
        "conf_stanzas": desired,
        "splunk": {"home": "/opt/splunk"},
    }
    variables["config_map_preserve_kvstore_backend"] = Templar(
        loader=loader, variables=variables
    ).template(reconcile["vars"]["config_map_preserve_kvstore_backend"])
    assert variables["config_map_preserve_kvstore_backend"] is preserve

    for stanza, option in [
        ("kvstore", "defaultKVStoreType"),
        ("kvstore", "kvserviceConnectionString"),
        ("kvstore", "postgresMigrateOnStartup"),
        ("general", "defaultKVStoreType"),
    ]:
        variables.update({
            "config_map_stanza_name": stanza,
            "config_map_stanza_settings": {option: "previous"},
            "config_map_stanza_setting": {"key": option, "value": "previous"},
        })
        condition = Conditional(loader=loader)
        condition.when = remove["when"]
        should_remove = condition.evaluate_conditional(
            Templar(loader=loader, variables=variables), variables
        )
        assert should_remove is not (
            preserve and stanza == "kvstore" and option == "defaultKVStoreType"
        )


@pytest.mark.parametrize("saved_backend", ["local", "external"])
def test_actual_tasks_preserve_cutover_and_enforce_old_image_policy(tmp_path, saved_backend):
    """Exercise real ini_file writes, cleanup, and managed metadata locally."""
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    server_conf = local / "server.conf"
    managed = local / ".server.conf.splunk-ansible-managed.yml"
    (home / "etc/splunk.version").write_text("VERSION=10.6.0\nBUILD=test\n")
    user = getpass.getuser()
    variables = {
        "splunk": {"home": str(home), "exec": "/must-not-call-splunk-cli",
                   "user": user, "group": str(os.getgid()),
                   "enable_service": False,
                   "kvstore": {"default_kvstore_type": "external"}},
        "conf_directory": str(local),
        "conf_file": "server.conf",
        "reconcile_config_map_values": True,
        "hide_password": False,
        "ansible_python_interpreter": sys.executable,
        "ansible_system": "Linux",
    }

    def include(task_file, **extra):
        return {"include_tasks": str(TASK_DIR / task_file), **extra}

    tasks = [
        include("stop_splunk.yml"),
        include("set_default_kvstore_type.yml"),
        include("set_config_file.yml", vars={
            "conf_stanzas": {"kvstore": {"defaultKVStoreType": "external",
                                         "postgresMigrateOnStartup": "true"}},
        }),
        include("set_default_kvstore_type.yml"),
        {"slurp": {"src": str(server_conf)}, "register": "old_image_conf"},
        {"assert": {"that": [
            "'defaultKVStoreType = local' in (old_image_conf.content | b64decode)",
            "'postgresMigrateOnStartup = false' in (old_image_conf.content | b64decode)",
        ]}},
        {"set_fact": {"kvstore_installed_splunk_version": ["10.9.0"]}},
        # Splunk can change the backend after SOK records its desired value.
        {"ini_file": {"path": str(server_conf), "section": "kvstore",
                      "option": "defaultKVStoreType", "value": saved_backend}},
        include("set_default_kvstore_type.yml"),
        include("set_config_file.yml", vars={
            "conf_stanzas": {"kvstore": {"kvserviceConnectionString": "https://kvservice"}},
        }),
        {"slurp": {"src": str(server_conf)}, "register": "handoff_conf"},
        {"assert": {"that": [
            "'defaultKVStoreType = %s' in (handoff_conf.content | b64decode)" % saved_backend,
            "'postgresMigrateOnStartup' not in (handoff_conf.content | b64decode)",
        ]}},
        # Model the core startup helper's persisted flag, then reconcile again.
        {"ini_file": {"path": str(server_conf), "section": "kvstore",
                      "option": "postgresMigrateOnStartup", "value": "true"}},
        include("set_config_file.yml", vars={
            "conf_stanzas": {"kvstore": {"kvserviceConnectionString": "https://kvservice"}},
        }),
    ]
    _run_tasks(tmp_path, variables, tasks)
    conf = configparser.ConfigParser()
    conf.read(server_conf)
    assert conf["kvstore"]["defaultKVStoreType"] == saved_backend
    assert conf["kvstore"]["postgresMigrateOnStartup"] == "true"
    ownership = yaml.safe_load(managed.read_text())
    assert ownership == {"kvstore": {"kvserviceConnectionString": "https://kvservice"}}


def test_fresh_kvservice_config_is_visible_to_first_status_command(tmp_path):
    home = tmp_path / "splunk"
    local = home / "etc/system/local"
    local.mkdir(parents=True)
    server_conf = local / "server.conf"
    (home / "etc/splunk.version").write_text("VERSION=10.9.0\nBUILD=test\n")
    ftr = home / "ftr"
    ftr.touch()
    cli_observed_endpoint = tmp_path / "cli-observed-endpoint"
    fake_splunk = tmp_path / "splunk-cli"
    # Check the input available to native FTR, rather than duplicate core policy.
    fake_splunk.write_text(
        "#!%s\n" % sys.executable
        + "import configparser, pathlib, sys\n"
        + "conf = configparser.ConfigParser()\n"
        + "conf.read(%r)\n" % str(server_conf)
        + "endpoint = conf.get('kvstore', 'kvserviceConnectionString', fallback='')\n"
        + "if endpoint == 'https://kvservice' and pathlib.Path(%r).exists():\n" % str(ftr)
        + "    pathlib.Path(%r).write_text(endpoint)\n" % str(cli_observed_endpoint)
        + "    pathlib.Path(%r).unlink()\n" % str(ftr)
        + "sys.exit(1)\n"
    )
    fake_splunk.chmod(0o755)
    user = getpass.getuser()
    variables = {
        "splunk": {"home": str(home), "exec": str(fake_splunk),
                   "role": "splunk_standalone", "user": user, "group": str(os.getgid()),
                   "pass4SymmKey": "test-key", "kvstore": {},
                   "conf": {"server": {"content": {
                       "kvstore": {"kvserviceConnectionString": "https://kvservice"},
                   }}}},
        "hide_password": False,
        "ansible_python_interpreter": sys.executable,
        "ansible_system": "Linux",
    }
    main_tasks = yaml.safe_load((TASK_DIR / "main.yml").read_text())
    selected = []
    for task in main_tasks:
        if task.get("include_tasks") in {
            "set_config_file.yml", "set_default_kvstore_type.yml",
            "set_general_symmkey_password.yml",
        }:
            task["include_tasks"] = str(TASK_DIR / task["include_tasks"])
            selected.append(task)
    _run_tasks(tmp_path, variables, selected)
    assert cli_observed_endpoint.read_text() == "https://kvservice"
    assert not ftr.exists()
