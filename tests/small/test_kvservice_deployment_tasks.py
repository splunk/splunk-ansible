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
    ("marker_exists", "scope", "should_remove"),
    [
        (False, None, False),
        (True, None, True),
        (True, "platform", True),
        (True, "deployment", False),
    ],
)
def test_managed_settings_cleanup_condition(marker_exists, scope, should_remove):
    cleanup = task_named(
        "Remove previous Ansible-managed deployment-scoped KVService settings"
    )
    variables = {
        "kvservice_managed_config": {"stat": {"exists": marker_exists}},
        "splunk": {"kvstore": {"kvservice_scope": scope}},
    }
    jinja = Environment()
    assert all(
        jinja.compile_expression(condition)(**variables) for condition in cleanup["when"]
    ) is should_remove


def test_managed_settings_cleanup_scope():
    cleanup = task_named(
        "Remove previous Ansible-managed deployment-scoped KVService settings"
    )
    removed_settings = {
        (task["ini_file"]["section"], task["ini_file"]["option"])
        for task in cleanup["block"]
        if "ini_file" in task and task["ini_file"]["state"] == "absent"
    }
    assert removed_settings == {
        ("kvstore", "kvserviceMode"),
        ("kvstore", "kvserviceScope"),
        ("kvstore", "kvserviceDeploymentMode"),
        ("scs", "tenant"),
        ("scs", "environment"),
    }
    assert any(
        task.get("file", {}).get("state") == "absent" for task in cleanup["block"]
    )


@pytest.mark.parametrize("scope,creates_marker", [("deployment", True), ("platform", False), (None, False)])
def test_deployment_scope_creates_marker(scope, creates_marker):
    marker = task_named("Mark deployment-scoped KVService settings as Ansible-managed")
    variables = {"splunk": {"kvstore": {"kvservice_scope": scope}}}
    assert all(
        Environment().compile_expression(condition)(**variables)
        for condition in marker["when"]
    ) is creates_marker
    # Keep the marker path so volumes managed by earlier releases are recognized.
    assert marker["copy"]["dest"].endswith("/.kvservice-single-customer-managed")


@pytest.mark.parametrize("scope", ["deployment", "platform"])
def test_scope_replaces_legacy_settings(scope):
    scope_task = task_named("Set KVService scope")
    assert scope_task["ini_file"]["option"] == "kvserviceScope"
    value = scope_task["ini_file"]["value"]
    jinja = Environment()
    variables = {"splunk": {"kvstore": {"kvservice_scope": scope}}}
    assert jinja.from_string(value).render(**variables) == scope
    assert all(jinja.compile_expression(condition)(**variables) for condition in scope_task["when"])

    for name, option in (
        ("Remove legacy KVService deployment mode when configuring scope", "kvserviceDeploymentMode"),
        ("Remove legacy KVService mode when configuring scope", "kvserviceMode"),
    ):
        cleanup = task_named(name)
        assert cleanup["ini_file"]["option"] == option
        assert cleanup["ini_file"]["state"] == "absent"
        assert all(jinja.compile_expression(condition)(**variables) for condition in cleanup["when"])

    # An already configured scope must not be removed before being rewritten.
    assert not any(
        task.get("ini_file", {}).get("option") == "kvserviceScope"
        and task["ini_file"].get("state") == "absent"
        for task in TASKS
    )


@pytest.mark.parametrize("kvstore", [{}, {"kvservice_scope": ""}, {"kvservice_scope": None}])
def test_missing_scope_skips_scope_and_legacy_mode_writes(kvstore):
    variables = {"splunk": {"kvstore": kvstore}}
    jinja = Environment()
    for name in (
        "Set KVService scope",
        "Remove legacy KVService deployment mode when configuring scope",
        "Remove legacy KVService mode when configuring scope",
    ):
        task = task_named(name)
        assert not all(jinja.compile_expression(condition)(**variables) for condition in task["when"])


def test_sok_app_server_conf_is_rebuilt_from_current_defaults():
    tasks = yaml.safe_load(
        (TASK_FILE.parent / "remove_stale_sok_conf.yml").read_text()
    )
    cleanup = tasks[0]
    assert "{{ splunk.home }}/etc/apps/100-sok/local/server.conf" in cleanup["loop"]
