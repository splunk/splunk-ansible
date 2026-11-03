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
    ("marker_exists", "should_remove"),
    [
        (False, False),
        (True, True),
    ],
)
def test_managed_settings_cleanup_condition(marker_exists, should_remove):
    cleanup = task_named(
        "Remove previous Ansible-managed installation-scoped KVService settings"
    )
    variables = {
        "kvservice_managed_config": {"stat": {"exists": marker_exists}},
        "splunk": {"kvstore": {}},
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


def test_connection_string_creates_marker():
    marker = task_named("Mark KVService connection settings as Ansible-managed")
    assert marker["copy"]["content"] == "kvserviceConnectionString\n"
    assert marker["when"] == [
        "splunk.kvstore.kvservice_connection_string | default('') | length > 0"
    ]


def test_connection_string_is_written_without_scope_or_environment():
    connection = task_named("Set KVService connection string")
    assert connection["ini_file"]["option"] == "kvserviceConnectionString"
    jinja = Environment()
    url = "http://kvservice.default:8066"
    assert jinja.from_string(connection["ini_file"]["value"]).render(
        splunk={"kvstore": {"kvservice_connection_string": url}}
    ) == url
    assert all(
        task.get("ini_file", {}).get("option") != "kvserviceScope"
        for task in TASKS
    )


@pytest.mark.parametrize(
    ("marker_exists", "connection", "should_remove"),
    [(False, "", False), (True, "", True), (True, "https://host:8066", False)],
)
def test_connection_cleanup_requires_ownership(marker_exists, connection, should_remove):
    cleanup = task_named("Remove previous Ansible-managed KVService connection settings")
    variables = {
        "kvservice_connection_managed": {"stat": {"exists": marker_exists}},
        "splunk": {"kvstore": {"kvservice_connection_string": connection}},
    }
    assert all(
        Environment().compile_expression(condition)(**variables)
        for condition in cleanup["when"]
    ) is should_remove
    assert {
        task["ini_file"]["option"]
        for task in cleanup["block"] if "ini_file" in task
    } == {"kvserviceConnectionString"}


def test_cloud_environment_remains_supported():
    task = task_named("Set KVService environment")
    assert task["ini_file"]["section"] == "scs"
    assert task["ini_file"]["option"] == "environment"
    assert task["ini_file"]["value"] == "{{ splunk.scs.environment }}"


def test_sok_app_server_conf_is_rebuilt_from_current_defaults():
    tasks = yaml.safe_load(
        (TASK_FILE.parent / "remove_stale_sok_conf.yml").read_text()
    )
    cleanup = tasks[0]
    assert "{{ splunk.home }}/etc/apps/100-sok/local/server.conf" in cleanup["loop"]
