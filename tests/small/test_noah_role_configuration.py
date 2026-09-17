#!/usr/bin/env python
"""Contract tests for Noah provisioning and shared SHC startup behavior."""

from __future__ import absolute_import

import os
import sys

import yaml


FILE_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_DIR = os.path.join(FILE_DIR, "..", "..")
sys.path.insert(0, os.path.join(REPO_DIR, "roles", "splunk_noah", "filter_plugins"))

splunk_conf = __import__("splunk_conf")


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


def test_common_role_configures_a_fresh_deployer_before_splunkd_start():
    tasks = load_yaml("roles/splunk_common/tasks/main.yml")
    status = named_task(tasks, "Check SHC participant process state before declarative configuration")
    prestart = named_task(tasks, "Configure SHC deployer before splunkd starts")
    deployer_tasks = load_yaml("roles/splunk_deployer/tasks/main.yml")
    late_reconcile = named_task(deployer_tasks, "Set deployer SHC key and label")

    assert "splunk_deployer" in status["when"][1]
    assert prestart["include_tasks"] == "configure_deployer_prestart.yml"
    assert "first_run | bool" in prestart["when"]
    assert "splunk_status.rc != 0" in prestart["when"]
    assert tasks.index(prestart) < next(
        i for i, task in enumerate(tasks) if task.get("include_tasks") == "start_splunk.yml"
    )
    assert "deployer_prestart_configured" in late_reconcile["when"]


def test_deployer_prestart_writes_and_validates_the_shc_contract():
    text = read_file("roles/splunk_common/tasks/configure_deployer_prestart.yml")

    assert 'section: "shclustering"' in text
    assert 'option: "pass4SymmKey"' in text
    assert 'option: "shcluster_label"' in text
    assert 'deployer_prestart_configured: true' in text
    assert "Restart the splunkd service" not in text


def test_pre_auth_keeps_noah_disabled_and_writes_a_safe_heartbeat():
    text = read_file("roles/splunk_noah/tasks/pre_auth.yml")
    assert "'true' if item.key == 'disabled'" in text
    assert "Keep Noah disabled during temporary authentication startup" in text
    assert "splunk_noah_client_profile.heartbeat_period" in text
    assert "noah_service_stanza" in text
    assert "splunk.conf is mapping" in text
    assert "splunk.conf is not mapping" in text
    assert "combine(item.value.content.noahService, recursive=true)" in text
    assert "| first" not in text
    assert "item.get('value', {}).get('directory')" in text
    assert "normalize_splunk_conf_path" in text
    assert "noah_service_stanza.get('pass4SymmKey', '')" in text
    assert 'loop: "{{ splunk_conf_effective }}"' in text
    # The Noah pass4SymmKey must come exclusively from
    # splunk.conf.server.content.noahService.pass4SymmKey (delivered via a
    # Kubernetes Secret). It must never fall back to splunk.pass4SymmKey,
    # which is the Splunk-to-Splunk [general] key — a different credential.
    assert "splunk.pass4SymmKey" not in text


def test_noah_role_normalizes_effective_server_files_for_shared_writer():
    pre_auth = load_yaml("roles/splunk_noah/tasks/pre_auth.yml")
    normalization = load_yaml("roles/splunk_noah/tasks/normalize_conf.yml")
    common = read_file("roles/splunk_common/tasks/main.yml")

    include = named_task(pre_auth, "Normalize list-form server.conf at the Noah role boundary")
    assert include["include_tasks"] == "normalize_conf.yml"
    assert include["when"] == "splunk.conf is not mapping"

    normalize = named_task(normalization, "Normalize list-form server.conf entries by effective file")
    assert "normalize_splunk_conf_entries" in normalize["set_fact"]["splunk_conf_effective"]
    assert normalize["no_log"] is True

    # This is the value consumed by the generic config writer. Using a separate
    # fact also works when splunk.conf itself came from immutable extra-vars.
    assert "splunk_conf_effective | default(splunk.conf)" in common

    for task_file in (
        "roles/splunk_indexer/tasks/indexer_clustering.yml",
        "roles/splunk_indexer/tasks/setup_multisite.yml",
    ):
        assert "splunk_conf_effective | default(splunk.conf)" in read_file(task_file)


def test_noah_filters_expose_shared_normalization_and_path_identity():
    filters = splunk_conf.FilterModule().filters()
    assert "normalize_splunk_conf_entries" in filters
    assert filters["normalize_splunk_conf_path"](
        "/opt//splunk/etc/./system/local/"
    ) == "/opt/splunk/etc/system/local"


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


def test_shc_retries_are_mode_specific_but_early_restart_is_suppressed():
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


def test_shc_prestart_restarts_only_after_local_key_adoption():
    role_tasks = load_yaml("roles/splunk_search_head/tasks/main.yml")
    cluster_formation = next(
        task for task in role_tasks
        if task.get("include_tasks") == "search_head_clustering.yml"
    )
    role_restart_check = next(
        task for task in role_tasks
        if task.get("include_tasks") == "../../../roles/splunk_common/tasks/check_for_required_restarts.yml"
    )
    cluster_tasks = load_yaml("roles/splunk_search_head/tasks/search_head_clustering.yml")
    early_flush = named_task(cluster_tasks, "Flush restart handlers")
    convergence = named_task(cluster_tasks, "Wait for Noah SHC member key adoption")
    captain_state = named_task(cluster_tasks, "Record whether this Noah SHC member is the elected captain")
    secret_metadata = named_task(cluster_tasks, "Read Noah SHC common-secret metadata")
    pid_metadata = named_task(cluster_tasks, "Read current splunkd PID-file metadata")
    secret_version = named_task(cluster_tasks, "Build the Noah SHC common-secret version marker")
    marker_metadata = named_task(cluster_tasks, "Check for a previously loaded Noah SHC common-secret version")
    marker_contents = named_task(cluster_tasks, "Read the previously loaded Noah SHC common-secret version")
    restart_decision = named_task(cluster_tasks, "Decide whether this Noah SHC member must reload the common secret")
    captain_guard = named_task(cluster_tasks, "Defer an uncoordinated restart of the elected Noah SHC captain")
    post_convergence_restart = named_task(
        cluster_tasks, "Restart Noah SHC member after common-secret convergence"
    )
    version_record = named_task(
        cluster_tasks, "Record the common-secret version loaded by this Noah SHC member"
    )
    restart_record = named_task(cluster_tasks, "Record the Noah SHC post-convergence restart")
    site_tasks = load_yaml("site.yml")[0]["tasks"][0]["block"]
    global_restart_check = named_task(site_tasks, "Check all instances for required restarts")
    restart_tasks = load_yaml("roles/splunk_common/tasks/check_for_required_restarts.yml")
    required_restart = named_task(restart_tasks, "Check for required restarts")
    restart_fact = named_task(restart_tasks, "Set fact if restart was triggered")

    assert role_tasks.index(cluster_formation) < role_tasks.index(role_restart_check)
    assert "when" not in role_restart_check
    assert early_flush["when"] == "not (shc_prestart_configured | default(false) | bool)"
    assert convergence["splunk_api"]["url"] == (
        "/services/replication/configuration/health?unpublished=1&output_mode=json"
    )
    assert convergence["changed_when"] is False
    assert "splunk_noah_enabled | default(false) | bool" in convergence["when"]
    assert "not splunk_search_head_captain | bool" in convergence["when"]
    assert convergence["retries"] == "{{ shc_sync_retry_num }}"
    assert convergence["delay"] == "{{ retry_delay }}"
    convergence_contract = " ".join(str(condition) for condition in convergence["until"])
    assert "status == 200" in convergence_contract
    assert "entry[0].name" in convergence_contract
    assert "unpublished" in convergence_contract
    assert "Number of unpublished changes" in convergence_contract
    assert "['0', '0 (this instance is the captain)']" in convergence_contract
    assert "0 (this instance is the captain)" in captain_state["set_fact"]["noah_shc_local_is_current_captain"]
    assert secret_metadata["stat"]["path"] == "{{ splunk.home }}/etc/auth/splunk.secret"
    assert secret_metadata["stat"]["get_checksum"] is False
    assert secret_metadata["changed_when"] is False
    assert secret_metadata["failed_when"] == "not noah_shc_common_secret.stat.exists"
    assert secret_metadata["no_log"] is True
    assert pid_metadata["stat"]["path"] == "{{ splunk.pid }}"
    assert pid_metadata["stat"]["get_checksum"] is False
    assert pid_metadata["changed_when"] is False
    assert pid_metadata["failed_when"] == "not noah_shc_splunkd_pid_file.stat.exists"
    assert pid_metadata["no_log"] is True
    assert "stat.inode" in secret_version["set_fact"]["noah_shc_common_secret_version"]
    assert "stat.mtime" in secret_version["set_fact"]["noah_shc_common_secret_version"]
    assert marker_metadata["stat"]["path"] == "{{ splunk.pid }}.noah-shc-secret-version"
    assert marker_metadata["stat"]["get_checksum"] is False
    assert marker_contents["slurp"]["src"] == "{{ splunk.pid }}.noah-shc-secret-version"
    assert "noah_shc_secret_version_marker.stat.exists | default(false)" in marker_contents["when"]
    decision = restart_decision["set_fact"]["noah_shc_common_secret_restart_required"]
    assert "noah_shc_common_secret.stat.mtime" in decision
    assert "noah_shc_splunkd_pid_file.stat.mtime" in decision
    assert ">=" in decision
    assert "noah_shc_loaded_secret_version.content" in decision
    assert "noah_shc_common_secret_version" in decision
    assert "noah_shc_local_is_current_captain | default(false) | bool" in captain_guard["when"]
    assert "noah_shc_common_secret_restart_required | default(false) | bool" in captain_guard["when"]
    assert post_convergence_restart["include_tasks"] == (
        "../../../roles/splunk_common/handlers/restart_splunk.yml"
    )
    assert "not (noah_shc_local_is_current_captain | default(false) | bool)" in post_convergence_restart["when"]
    assert "noah_shc_common_secret_restart_required | default(false) | bool" in post_convergence_restart["when"]
    assert version_record["copy"]["dest"] == "{{ splunk.pid }}.noah-shc-secret-version"
    assert version_record["copy"]["mode"] == "0600"
    assert restart_record["set_fact"]["splunk_restart_triggered"] is True
    assert post_convergence_restart["when"] == restart_record["when"]
    assert cluster_tasks.index(convergence) < cluster_tasks.index(secret_metadata)
    assert cluster_tasks.index(secret_metadata) < cluster_tasks.index(pid_metadata)
    assert cluster_tasks.index(pid_metadata) < cluster_tasks.index(restart_decision)
    assert cluster_tasks.index(restart_decision) < cluster_tasks.index(captain_guard)
    assert cluster_tasks.index(captain_guard) < cluster_tasks.index(post_convergence_restart)
    assert cluster_tasks.index(post_convergence_restart) < cluster_tasks.index(version_record)
    assert cluster_tasks.index(version_record) < cluster_tasks.index(restart_record)
    assert "splunk_restart_triggered is not defined or not splunk_restart_triggered" in global_restart_check["when"]
    assert "not (shc_prestart_defer_initial_restart | default(false) | bool)" in global_restart_check["when"]
    assert required_restart["changed_when"] == "restart_required.status == 200"
    assert restart_fact["set_fact"]["splunk_restart_triggered"] is True
    assert restart_fact["when"] == "restart_required.status == 200"


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
