"""Preserve MSI-managed file ownership during Windows configuration edits."""

from pathlib import Path

import pytest
from ansible.executor.task_executor import remove_omit
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar


ROLE_TASKS = Path(__file__).resolve().parents[2] / "roles" / "splunk_common" / "tasks"
OMIT = "__ownership_test_omit__"
CONFIG_TASKS = [
    ("enable_splunkd_ssl.yml", "Enable Splunkd SSL"),
    ("enable_splunkd_ssl.yml", "Set Splunkd CA"),
    ("enable_splunkd_ssl.yml", "Set Splunkd cert"),
    ("enable_splunkd_ssl.yml", "Set Splunkd SSL password"),
    ("set_splunk_connection_timeout.yml", "Set Splunkd Connection Timeout"),
]


def _module_args(filename, task_name, ansible_system, ssl_enabled=True):
    loader = DataLoader()
    tasks = loader.load_from_file(str(ROLE_TASKS / filename))
    task = next(task for task in tasks if task.get("name") == task_name)
    variables = {
        "ansible_system": ansible_system,
        "omit": OMIT,
        "splunk": {
            "home": "/opt/splunk",
            "user": "configured-user",
            "group": "configured-group",
            "connection_timeout": 180,
            "ssl": {
                "enable": ssl_enabled,
                "ca": "/opt/splunk/etc/auth/ca.pem",
                "cert": "/opt/splunk/etc/auth/server.pem",
                "password": "test-password",
            },
        },
    }
    args = Templar(loader=loader, variables=variables).template(task["ini_file"])
    return remove_omit(args, OMIT)


@pytest.mark.parametrize("filename,task_name", CONFIG_TASKS)
@pytest.mark.parametrize("ansible_system", ["CYGWIN_NT-10.0-20348", "Win32NT"])
def test_windows_configuration_does_not_request_posix_ownership(
    filename, task_name, ansible_system
):
    args = _module_args(filename, task_name, ansible_system)
    assert "owner" not in args
    assert "group" not in args


@pytest.mark.parametrize("filename,task_name", CONFIG_TASKS)
def test_linux_configuration_retains_configured_ownership(filename, task_name):
    args = _module_args(filename, task_name, "Linux")
    assert args["owner"] == "configured-user"
    assert args["group"] == "configured-group"


@pytest.mark.parametrize("ansible_system", ["CYGWIN_NT-10.0-20348", "Win32NT", "Linux"])
@pytest.mark.parametrize("ssl_enabled,expected_state", [(True, "absent"), (False, "present")])
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
