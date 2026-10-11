from pathlib import Path

import pytest
import yaml
from jinja2 import Environment


TASK_FILE = (
    Path(__file__).resolve().parents[2]
    / "roles/splunk_common/tasks/set_kvservice_deployment.yml"
)
TASKS = yaml.safe_load(TASK_FILE.read_text())


def task_named(name):
    return next(task for task in TASKS if task["name"] == name)


@pytest.mark.parametrize(
    ("marker_exists", "mode", "should_remove"),
    [
        (False, None, False),
        (True, None, True),
        (True, "multiCustomer", True),
        (True, "singleCustomer", False),
    ],
)
def test_managed_settings_cleanup_condition(marker_exists, mode, should_remove):
    cleanup = task_named(
        "Remove previous Ansible-managed single-customer KVService settings"
    )
    variables = {
        "kvservice_managed_config": {"stat": {"exists": marker_exists}},
        "splunk": {"kvstore": {"deployment_mode": mode}},
    }
    jinja = Environment()
    assert all(
        jinja.compile_expression(condition)(**variables) for condition in cleanup["when"]
    ) is should_remove


def test_managed_settings_cleanup_scope():
    cleanup = task_named(
        "Remove previous Ansible-managed single-customer KVService settings"
    )
    removed_settings = {
        (task["ini_file"]["section"], task["ini_file"]["option"])
        for task in cleanup["block"]
        if "ini_file" in task and task["ini_file"]["state"] == "absent"
    }
    assert removed_settings == {
        ("kvstore", "kvserviceDeploymentMode"),
        ("scs", "tenant"),
        ("scs", "environment"),
    }
    assert any(
        task.get("file", {}).get("state") == "absent" for task in cleanup["block"]
    )


def test_single_customer_mode_creates_marker():
    marker = task_named("Mark single-customer KVService settings as Ansible-managed")
    assert marker["copy"]["content"] == "singleCustomer\n"
    assert marker["when"] == [
        "splunk.kvstore.deployment_mode | default('') == 'singleCustomer'"
    ]
