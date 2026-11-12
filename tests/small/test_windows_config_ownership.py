"""Preserve MSI-managed file ownership during Windows configuration edits."""

from pathlib import Path

import pytest
from ansible.executor.task_executor import remove_omit
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar

ROLE_TASKS = Path(__file__).resolve().parents[2] / "roles" / "splunk_common" / "tasks"
OMIT = "__ownership_test_omit__"
CONFIG_TASKS = [
    ("enable_splunkd_ssl.yml", "Enable Splunkd SSL"),
    ("enable_splunkd_ssl.yml", "Set Splunkd CA"),
    ("enable_splunkd_ssl.yml", "Set Splunkd cert"),
    ("enable_splunkd_ssl.yml", "Set Splunkd SSL password"),
    ("set_splunk_connection_timeout.yml", "Set Splunkd Connection Timeout"),
    ("configure_mgmt_port.yml", "Configure to set Mgmt Mode as tcp (Allows only TCP)"),
    ("enable_splunkweb_ssl.yml", "Enable Web SSL"),
    ("enable_splunkweb_ssl.yml", "Set Web certificate path"),
    ("enable_splunkweb_ssl.yml", "Set Web private key path"),
    ("enable_splunkweb_ssl.yml", "Set Web private key password"),
    ("set_config_stanza.yml", "Set stanza {{ stanza_name }}"),
    ("set_config_stanza.yml", "Set options in {{ stanza_name }}"),
    ("set_config_file.yml", "Set owner, group and mode of {{ conf_file }}"),
    ("set_config_file.yml", "Record ConfigMap-owned values in {{ conf_file }}"),
    (
        "remove_config_map_stanza.yml",
        "Remove ConfigMap-owned options in {{ config_map_stanza_name }}",
    ),
]
RESTRICTIVE_MODE_TASKS = [
    task
    for task in CONFIG_TASKS
    if task[0]
    in ("enable_splunkweb_ssl.yml", "set_config_stanza.yml", "set_config_file.yml")
]


def _variables(ansible_system, ssl_enabled=True):
    return {
        "ansible_system": ansible_system,
        "omit": OMIT,
        "conf_directory": "/opt/splunk/etc/system/local",
        "conf_file": "server.conf",
        "conf_stanzas": {"general": {"serverName": "test-server"}},
        "stanza_name": "general",
        "stanza_setting": {"key": "serverName", "value": "test-server"},
        "config_map_stanza_name": "general",
        "config_map_stanza_setting": {"key": "obsoleteOption"},
        "splunk": {
            "home": "/opt/splunk",
            "user": "configured-user",
            "group": "configured-group",
            "connection_timeout": 180,
            "http_enableSSL": True,
            "http_enableSSL_cert": "/opt/splunk/etc/auth/web-cert.pem",
            "http_enableSSL_privKey": "/opt/splunk/etc/auth/web-key.pem",
            "http_enableSSL_privKey_password": "test-password",
            "ssl": {
                "enable": ssl_enabled,
                "ca": "/opt/splunk/etc/auth/ca.pem",
                "cert": "/opt/splunk/etc/auth/server.pem",
                "password": "test-password",
            },
        },
    }


def _load_task(loader, filename, task_name):
    tasks = loader.load_from_file(str(ROLE_TASKS / filename))
    return next(task for task in tasks if task.get("name") == task_name)


def _module_args(filename, task_name, ansible_system, ssl_enabled=True):
    loader = DataLoader()
    task = _load_task(loader, filename, task_name)
    module = next(
        name
        for name in ("splunk_config", "ini_file", "lineinfile", "file", "copy")
        if name in task
    )
    args = Templar(
        loader=loader, variables=_variables(ansible_system, ssl_enabled)
    ).template(task[module])
    return remove_omit(args, OMIT)


@pytest.mark.parametrize("filename,task_name", CONFIG_TASKS)
@pytest.mark.parametrize("ansible_system", ["CYGWIN_NT-10.0-20348", "Win32NT"])
def test_windows_configuration_uses_the_platform_aware_action(
    filename, task_name, ansible_system
):
    loader = DataLoader()
    task = _load_task(loader, filename, task_name)
    assert "splunk_config" in task
    args = _module_args(filename, task_name, ansible_system)
    expected_module = {
        "Set stanza {{ stanza_name }}": "lineinfile",
        "Set owner, group and mode of {{ conf_file }}": "file",
        "Record ConfigMap-owned values in {{ conf_file }}": "copy",
    }.get(task_name, "ini_file")
    assert args["module"] == expected_module
    assert args["home"] == "/opt/splunk"


@pytest.mark.parametrize("filename,task_name", CONFIG_TASKS)
def test_linux_configuration_retains_configured_ownership(filename, task_name):
    args = _module_args(filename, task_name, "Linux")
    assert args["owner"] == "configured-user"
    assert args["group"] == "configured-group"


@pytest.mark.parametrize("filename,task_name", RESTRICTIVE_MODE_TASKS)
def test_unix_configuration_writers_retain_restrictive_posix_modes(filename, task_name):
    args = _module_args(filename, task_name, "Linux")
    mode = args["mode"]
    # Ansible YAML accepts both integer octal and quoted octal modes.
    assert (int(mode, 8) if isinstance(mode, str) else mode) == 0o660


@pytest.mark.parametrize("ansible_system", ["CYGWIN_NT-10.0-20348", "Win32NT"])
@pytest.mark.parametrize(
    "role,expected",
    [("splunk_universal_forwarder", True), ("splunk_standalone", False)],
)
def test_windows_forwarder_management_configuration_is_reachable(
    ansible_system, role, expected
):
    loader = DataLoader()
    task = _load_task(
        loader,
        "configure_mgmt_port.yml",
        "Configure to set Mgmt Mode as tcp (Allows only TCP)",
    )
    variables = _variables(ansible_system)
    variables["installed_splunk_version"] = "10.2.9"
    variables["splunk"].update(role=role, splunk_http_enabled=False)
    conditional = Conditional(loader=loader)
    conditional.when = task["when"]
    assert (
        conditional.evaluate_conditional(
            Templar(loader=loader, variables=variables), variables
        )
        is expected
    )


@pytest.mark.parametrize("ansible_system", ["CYGWIN_NT-10.0-20348", "Win32NT", "Linux"])
@pytest.mark.parametrize(
    "ssl_enabled,expected_state", [(True, "absent"), (False, "present")]
)
def test_ownership_handling_preserves_ssl_configuration(
    ansible_system, ssl_enabled, expected_state
):
    args = _module_args(
        "enable_splunkd_ssl.yml", "Enable Splunkd SSL", ansible_system, ssl_enabled
    )
    assert args["section"] == "sslConfig"
    assert args["option"] == "enableSplunkdSSL"
    assert args["value"] == "false"
    assert args["state"] == expected_state


@pytest.mark.parametrize(
    "filename,task_name",
    [
        task
        for task in CONFIG_TASKS
        if task[0]
        in (
            "set_config_stanza.yml",
            "set_config_file.yml",
            "remove_config_map_stanza.yml",
        )
    ],
)
def test_configuration_helpers_retain_ownership_without_gathered_facts(
    filename, task_name
):
    loader = DataLoader()
    task = _load_task(loader, filename, task_name)
    module = next(
        name
        for name in ("splunk_config", "ini_file", "lineinfile", "file", "copy")
        if name in task
    )
    variables = _variables("Linux")
    del variables["ansible_system"]
    args = remove_omit(
        Templar(loader=loader, variables=variables).template(task[module]), OMIT
    )
    assert args["owner"] == "configured-user"
    assert args["group"] == "configured-group"
