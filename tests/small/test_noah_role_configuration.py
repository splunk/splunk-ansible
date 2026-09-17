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

    validation = load_yaml("roles/splunk_noah/tasks/validate.yml")
    role_validation = named_task(validation, "Validate the Splunk role supported by Noah mode")
    shared_secret_validation = named_task(
        validation, "Require a pre-shared encryption secret for Noah search heads"
    )

    assert "splunk.role in splunk_noah_role_profiles" in role_validation["assert"]["that"]
    assert "does not support SPLUNK_ROLE" in role_validation["assert"]["fail_msg"]
    shared_secret_contract = " ".join(shared_secret_validation["assert"]["that"])
    assert "splunk.splunk_secret" in shared_secret_contract
    assert "splunk.secret" in shared_secret_contract
    assert "length" in shared_secret_contract
    assert shared_secret_validation["when"] == 'splunk.role == "splunk_search_head"'
    assert "same Kubernetes Secret" in shared_secret_validation["assert"]["fail_msg"]


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


def test_common_role_configures_a_stopped_license_peer_before_splunkd_start():
    tasks = load_yaml("roles/splunk_common/tasks/main.yml")
    status = named_task(
        tasks, "Check Splunk process state before declarative license configuration"
    )
    prestart = named_task(tasks, "Configure the license peer before splunkd starts")
    start_index = next(
        i for i, task in enumerate(tasks)
        if task.get("include_tasks") == "start_splunk.yml"
    )

    assert status["include_tasks"] == "get_splunk_status.yml"
    assert 'splunk.role != "splunk_license_master"' in status["when"]
    assert "splunk.license_master_url is defined" in status["when"]
    assert prestart["include_tasks"] == "configure_license_peer_prestart.yml"
    assert "first_run | bool" not in prestart["when"]
    assert "splunk_status.rc != 0" in prestart["when"]
    assert 'splunk.role != "splunk_license_master"' in prestart["when"]
    assert "splunk.license_master_url is defined" in prestart["when"]
    assert "splunk_noah_enabled" not in str(prestart["when"])
    assert tasks.index(prestart) < start_index


def test_fresh_license_peer_is_declarative_and_skips_the_post_start_edit():
    prestart_tasks = load_yaml(
        "roles/splunk_common/tasks/configure_license_peer_prestart.yml"
    )
    writer = named_task(prestart_tasks, "Write the license manager URI before splunkd starts")
    old_alias = named_task(
        prestart_tasks, "Remove the incompatible license manager URI alias"
    )
    version = named_task(
        prestart_tasks, "Select the supported license manager URI setting"
    )
    validation = named_task(
        prestart_tasks, "Validate effective pre-start license configuration"
    )
    recorded = named_task(
        prestart_tasks, "Record declarative pre-start license configuration"
    )
    license_tasks = load_yaml("roles/splunk_common/tasks/add_splunk_license.yml")
    post_start_include = named_task(license_tasks, "Set as license slave")
    post_start_tasks = load_yaml("roles/splunk_common/tasks/set_as_license_slave.yml")
    post_start_edit = named_task(post_start_tasks, "Set node as license slave")

    assert writer["ini_file"]["section"] == "license"
    assert writer["ini_file"]["option"] == "{{ license_peer_uri_option }}"
    assert writer["ini_file"]["value"] == "{{ splunk.license_master_url }}"
    assert old_alias["ini_file"]["state"] == "absent"
    assert "license_peer_uri_option == 'manager_uri'" in old_alias["ini_file"]["option"]
    assert "version('9.0.0', '>=')" in version["set_fact"]["license_peer_uri_option"]
    assert "manager_uri" in version["set_fact"]["license_peer_uri_option"]
    assert "master_uri" in version["set_fact"]["license_peer_uri_option"]
    assert "license_peer_uri_option" in validation["assert"]["that"][0]
    assert recorded["set_fact"]["license_peer_prestart_configured"] is True
    assert "license_peer_prestart_configured" not in str(post_start_include["when"])
    assert (
        "not (license_peer_prestart_configured | default(false) | bool)"
        == post_start_edit["when"]
    )


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


def test_preferred_captaincy_is_declarative_for_stopped_shc_members():
    prestart_tasks = load_yaml("roles/splunk_common/tasks/configure_shc_prestart.yml")
    preferred = named_task(
        prestart_tasks, "Configure preferred captaincy before splunkd starts"
    )
    validation = named_task(
        prestart_tasks, "Validate effective pre-start SHC configuration"
    )
    search_head_tasks = load_yaml(
        "roles/splunk_search_head/tasks/search_head_clustering.yml"
    )
    post_start = named_task(search_head_tasks, "Set desired preferred captaincy")

    assert preferred["ini_file"]["section"] == "shclustering"
    assert preferred["ini_file"]["option"] == "preferred_captain"
    assert "shc_prestart_preferred_captain" in preferred["ini_file"]["value"]
    assert preferred["when"] == "splunk.preferred_captaincy | default(false) | bool"
    assert any("preferred_captain = " in assertion for assertion in validation["assert"]["that"])
    assert "not (shc_prestart_configured | default(false) | bool)" in post_start["when"]


def test_running_shc_keeps_post_start_preferred_captain_reconciliation():
    tasks = load_yaml("roles/splunk_search_head/tasks/search_head_clustering.yml")
    preferred = named_task(tasks, "Set desired preferred captaincy")

    assert preferred["splunk_api"]["body"]["preferred_captain"] == (
        "{{ splunk_search_head_captain | bool | lower }}"
    )
    assert "splunk_search_head_captain is defined and splunk.preferred_captaincy | bool" in preferred["when"]
    assert "not (shc_prestart_configured | default(false) | bool)" in preferred["when"]


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


def test_shc_prestart_runs_one_post_formation_conditional_restart_check():
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
    site_tasks = load_yaml("site.yml")[0]["tasks"][0]["block"]
    global_restart_check = named_task(site_tasks, "Check all instances for required restarts")
    restart_tasks = load_yaml("roles/splunk_common/tasks/check_for_required_restarts.yml")
    required_restart = named_task(restart_tasks, "Check for required restarts")
    restart_fact = named_task(restart_tasks, "Set fact if restart was triggered")

    assert role_tasks.index(cluster_formation) < role_tasks.index(role_restart_check)
    # Keep one check after SHC formation. It only notifies the restart handler
    # when Splunk reports HTTP 200; HTTP 404 means the pre-start configuration
    # is already complete and the member remains running.
    assert "when" not in role_restart_check
    assert early_flush["when"] == "not (shc_prestart_configured | default(false) | bool)"
    assert "splunk_restart_triggered is not defined or not splunk_restart_triggered" in global_restart_check["when"]
    assert "not (shc_prestart_defer_initial_restart | default(false) | bool)" in global_restart_check["when"]


def test_running_shc_reconciliation_keeps_http_200_conditional_restart_check():
    role_tasks = load_yaml("roles/splunk_search_head/tasks/main.yml")
    role_restart_check = next(
        task for task in role_tasks
        if task.get("include_tasks") == "../../../roles/splunk_common/tasks/check_for_required_restarts.yml"
    )
    restart_tasks = load_yaml("roles/splunk_common/tasks/check_for_required_restarts.yml")
    required_restart = named_task(restart_tasks, "Check for required restarts")
    restart_fact = named_task(restart_tasks, "Set fact if restart was triggered")

    assert "when" not in role_restart_check
    assert required_restart["changed_when"] == "restart_required.status == 200"
    assert restart_fact["set_fact"]["splunk_restart_triggered"] is True
    assert restart_fact["when"] == "restart_required.status == 200"


def test_splunk_secret_tasks_redact_the_encryption_key():
    tasks = load_yaml("roles/splunk_common/tasks/set_splunk_secret.yml")
    legacy_secret = named_task(tasks, "Set the Splunk secret from splunk.secret")
    shared_secret = named_task(tasks, "Set the Splunk secret from splunk.splunk_secret")

    assert legacy_secret["no_log"] is True
    assert shared_secret["no_log"] is True


def test_noah_pass4symmkey_loop_items_are_redacted():
    pre_auth_tasks = load_yaml("roles/splunk_noah/tasks/pre_auth.yml")
    pre_auth_writer = named_task(
        pre_auth_tasks,
        "Write Noah service configuration for temporary authentication startup",
    )
    stanza_tasks = load_yaml("roles/splunk_common/tasks/set_config_stanza.yml")
    stanza_writer = next(
        task for task in stanza_tasks
        if str(task.get("name", "")).startswith("Set options in")
    )

    assert "item.key == 'pass4SymmKey'" in pre_auth_writer["no_log"]
    assert "stanza_setting.key == 'pass4SymmKey'" in stanza_writer["no_log"]
    assert "hide_password" in pre_auth_writer["no_log"]
    assert "hide_password" in stanza_writer["no_log"]


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
