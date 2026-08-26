#!/usr/bin/env python
"""Contract tests for Noah provisioning and shared SHC startup behavior."""

from __future__ import absolute_import

import os

import yaml


FILE_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_DIR = os.path.join(FILE_DIR, "..", "..")


def load_yaml(relative_path):
    with open(os.path.join(REPO_DIR, relative_path)) as stream:
        return yaml.safe_load(stream)


def read_file(relative_path):
    with open(os.path.join(REPO_DIR, relative_path)) as stream:
        return stream.read()


def named_task(tasks, name):
    return next(task for task in tasks if task.get("name") == name)


def test_noah_role_matrix_is_explicit_and_complete():
    defaults = load_yaml("roles/splunk_noah/defaults/main.yml")
    assert defaults["splunk_noah_role_profiles"] == {
        "splunk_indexer": {
            "client_role": "peer",
            "task_file": "indexer.yml",
            "heartbeat_period": "30",
        },
        "splunk_search_head": {
            "client_role": "search_client",
            "task_file": "search_head.yml",
            "heartbeat_period": "0",
        },
        "splunk_deployer": {
            "client_role": "none",
            "task_file": "deployer.yml",
            "heartbeat_period": "0",
        },
    }

    validation = read_file("roles/splunk_noah/tasks/validate.yml")
    assert "splunk.role in splunk_noah_role_profiles" in validation
    assert "does not support SPLUNK_ROLE" in validation


def test_common_role_calls_noah_at_the_two_lifecycle_boundaries():
    tasks = load_yaml("roles/splunk_common/tasks/main.yml")
    pre_auth = named_task(tasks, "Configure Noah safely before temporary authentication startup")
    post_config = named_task(tasks, "Configure the Noah client role before full splunkd startup")

    assert pre_auth["include_role"]["tasks_from"] == "pre_auth"
    assert post_config["include_role"]["tasks_from"] == "post_config"
    expected_gate = "splunk_noah_enabled | default(false) | bool"
    assert pre_auth["when"] == expected_gate
    assert post_config["when"] == expected_gate
    pre_index = tasks.index(pre_auth)
    auth_index = next(i for i, task in enumerate(tasks) if task.get("include_tasks") == "enable_admin_auth.yml")
    config_index = next(i for i, task in enumerate(tasks) if task.get("include_tasks") == "set_config_file.yml")
    post_index = tasks.index(post_config)
    start_index = next(i for i, task in enumerate(tasks) if task.get("include_tasks") == "start_splunk.yml")
    assert pre_index < auth_index
    assert config_index < post_index < start_index


def test_common_role_configures_every_stopped_shc_before_splunkd_start():
    tasks = load_yaml("roles/splunk_common/tasks/main.yml")
    prestart = named_task(tasks, "Configure SHC before splunkd starts")

    assert prestart["include_tasks"] == "configure_shc_prestart.yml"
    assert "splunk_search_head_cluster | bool" in prestart["when"]
    assert "splunk_noah_enabled" not in str(prestart["when"])
    assert tasks.index(prestart) < next(
        i for i, task in enumerate(tasks) if task.get("include_tasks") == "start_splunk.yml"
    )


def test_pre_auth_keeps_noah_disabled_and_writes_a_safe_heartbeat():
    text = read_file("roles/splunk_noah/tasks/pre_auth.yml")
    assert "'true' if item.key == 'disabled'" in text
    assert "Keep Noah disabled during temporary authentication startup" in text
    assert "splunk_noah_client_profile.heartbeat_period" in text
    assert "splunk.conf.server.content.noahService" in text


def test_each_supported_role_has_only_its_intended_noah_behavior():
    indexer = read_file("roles/splunk_noah/tasks/indexer.yml")
    search_head = read_file("roles/splunk_noah/tasks/search_head.yml")
    deployer = read_file("roles/splunk_noah/tasks/deployer.yml")

    assert "advertisedAddr" in indexer
    assert 'key: usePeers, value: "false"' in indexer
    assert "decouple_search_indexing" not in indexer

    assert 'key: usePeers, value: "true"' in search_head
    assert "decouple_search_indexing" in search_head
    assert "advertisedAddr" not in search_head
    assert "shclustering" not in search_head
    assert "replication_port://" not in search_head

    assert 'key: disabled, value: "true"' in deployer
    assert 'key: usePeers, value: "false"' in deployer
    assert "decouple_search_indexing" not in deployer


def test_search_head_prestart_configuration_is_shared_by_classic_and_noah():
    text = read_file("roles/splunk_common/tasks/configure_shc_prestart.yml")

    assert 'section: "shclustering"' in text
    assert 'section: "replication_port://{{ splunk.shc.replication_port }}"' in text
    assert 'option: "register_replication_address"' in text
    assert 'option: "search_head_uri"' in text
    assert "shc_prestart_configured: true" in text
    assert "shc_prestart_defer_initial_restart: true" in text
    assert "not (splunk_noah_enabled | default(false) | bool)" in text
    assert "shcclustering" not in text


def test_prestart_secret_is_only_written_for_a_fresh_etc_volume():
    tasks = load_yaml("roles/splunk_common/tasks/configure_shc_prestart.yml")
    secret = named_task(tasks, "Write the SHC symmetric key before the first splunkd start")

    assert secret["when"] == "first_run | bool"
    assert secret["no_log"] is True


def test_classic_indexer_peering_is_declarative_before_initial_start():
    prestart = read_file("roles/splunk_common/tasks/configure_shc_prestart.yml")
    peer_tasks = load_yaml("roles/splunk_common/tasks/peer_cluster_master.yml")
    peer_tcp = named_task(peer_tasks, "Peer cluster master TCP")

    assert 'section: "clustering"' in prestart
    assert 'value: "searchhead"' in prestart
    assert any("shc_prestart_indexer_peer_configured" in condition for condition in peer_tcp["when"])


def test_shc_retries_are_mode_specific_but_restart_elimination_is_shared():
    tasks = load_yaml("roles/splunk_search_head/tasks/search_head_clustering.yml")
    initialize = named_task(tasks, "Initialize SHC cluster config")
    wait_members = named_task(tasks, "Wait for all Noah SHC members before captain bootstrap")
    bootstrap = named_task(tasks, "Boostrap SHC captain")

    expected_retries = "{{ shc_sync_retry_num if (splunk_noah_enabled | default(false) | bool) else retry_num }}"
    assert initialize["retries"] == expected_retries
    assert bootstrap["retries"] == expected_retries
    assert "splunk_noah_enabled | default(false) | bool" in wait_members["when"]
    assert "not (shc_prestart_configured | default(false) | bool)" in initialize["when"]
    assert "not (shc_prestart_configured | default(false) | bool)" in bootstrap["changed_when"]


def test_initial_shc_restart_check_is_deferred_in_role_and_top_level_play():
    role_tasks = load_yaml("roles/splunk_search_head/tasks/main.yml")
    restart_check = next(
        task for task in role_tasks
        if task.get("include_tasks") == "../../../roles/splunk_common/tasks/check_for_required_restarts.yml"
    )
    site = read_file("site.yml")

    assert "not (shc_prestart_defer_initial_restart | default(false) | bool)" in restart_check["when"]
    assert "not (shc_prestart_defer_initial_restart | default(false) | bool)" in site


def test_late_server_name_reconciliation_uses_the_real_shc_stanza():
    text = read_file("roles/splunk_common/tasks/set_server_name.yml")

    assert "section: shclustering" in text
    assert "section: shcclustering" not in text


def test_restart_handler_keeps_the_existing_notification_contract():
    handlers = load_yaml("roles/splunk_common/handlers/main.yml")
    assert handlers[0]["name"] == "Restart the splunkd service"
    assert handlers[0]["include_tasks"] == "../handlers/restart_splunk.yml"

    restart_tasks = load_yaml("roles/splunk_common/handlers/restart_splunk.yml")
    noah = named_task(restart_tasks, "Restart Noah-managed splunkd - Via bounded CLI stop and start")
    classic = named_task(restart_tasks, "Restart classic splunkd service - Via CLI")
    assert "splunk_noah_enabled | default(false) | bool" in noah["when"]
    assert noah["shell"].startswith("set -e\n")
    assert " restart " not in noah["shell"]
    assert "not (splunk_noah_enabled | default(false) | bool)" in classic["when"]
    assert " restart --answer-yes --accept-license" in classic["command"]
