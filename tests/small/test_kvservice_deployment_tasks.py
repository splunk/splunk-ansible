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
        (True, "platformScoped", True),
        (True, "installationScoped", False),
    ],
)
def test_managed_settings_cleanup_condition(marker_exists, mode, should_remove):
    cleanup = task_named(
        "Remove previous Ansible-managed installation-scoped KVService settings"
    )
    variables = {
        "kvservice_managed_config": {"stat": {"exists": marker_exists}},
        "splunk": {"kvstore": {"kvservice_mode": mode}},
    }
    jinja = Environment()
    assert all(
        jinja.compile_expression(condition)(**variables) for condition in cleanup["when"]
    ) is should_remove


def test_managed_settings_cleanup_scope():
    cleanup = task_named(
        "Remove previous Ansible-managed installation-scoped KVService settings"
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
        ("kvstore", "defaultKVStoreType"),
        ("kvstore", "postgresMigrateOnStartup"),
        ("scs", "tenant"),
        ("scs", "environment"),
    }
    assert any(
        task.get("file", {}).get("state") == "absent" for task in cleanup["block"]
    )


def test_installation_scoped_mode_creates_marker():
    marker = task_named("Mark installation-scoped KVService settings as Ansible-managed")
    assert marker["copy"]["content"] == "installationScoped\n"
    assert marker["when"] == [
        "splunk.kvstore.kvservice_mode | default('') == 'installationScoped'"
    ]


def test_mode_replaces_legacy_settings():
    mode_task = task_named("Set KVService scope")
    assert mode_task["ini_file"]["option"] == "kvserviceScope"
    value = mode_task["ini_file"]["value"]
    jinja = Environment()
    for legacy_mode, scope in (("installationScoped", "deployment"), ("platformScoped", "platform")):
        assert jinja.from_string(value).render(splunk={"kvstore": {"kvservice_mode": legacy_mode}}) == scope

    for name, option in (
        ("Remove legacy KVService scope when configuring mode", "kvserviceScope"),
        ("Remove legacy KVService deployment mode when configuring mode", "kvserviceDeploymentMode"),
        ("Remove legacy KVService mode when configuring scope", "kvserviceMode"),
    ):
        cleanup = task_named(name)
        assert cleanup["ini_file"]["option"] == option
        assert cleanup["ini_file"]["state"] == "absent"


def test_sok_app_server_conf_is_rebuilt_from_current_defaults():
    tasks = yaml.safe_load(
        (TASK_FILE.parent / "remove_stale_sok_conf.yml").read_text()
    )
    cleanup = tasks[0]
    assert "{{ splunk.home }}/etc/apps/100-sok/local/server.conf" in cleanup["loop"]
