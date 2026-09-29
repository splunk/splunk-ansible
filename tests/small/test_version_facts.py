"""Regression tests for Splunk version facts used by install and upgrade tasks."""

from pathlib import Path

import pytest
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar


ROLE_TASKS = Path(__file__).resolve().parents[2] / "roles" / "splunk_common" / "tasks"
MANIFEST = "/opt/splunk/splunk-10.7.0.0-6da82bdc00cf-windows-x64-manifest"


def _task(loader, filename, name):
    tasks = loader.load_from_file(str(ROLE_TASKS / filename))
    return next(task for task in tasks if task.get("name") == name)


def _fact(loader, task, name, variables):
    scope = dict(variables, **task.get("vars", {}))
    return Templar(loader=loader, variables=scope).template(task["set_fact"][name])


def _version_facts(version, build_hash, manifest=MANIFEST, first_run=False):
    loader = DataLoader()
    build_location = (
        "https://repo.example/splunk-{}-{}-windows-x64.msi".format(version, build_hash)
    )
    splunk = {"build_location": build_location}
    target_task = _task(loader, "get_facts_target_version.yml", "Set target version fact (file)")
    target_version = _fact(loader, target_task, "splunk_target_version", {"splunk": splunk})

    current_task = _task(loader, "get_facts.yml", "Set current version fact")
    variables = {
        "splunk": splunk,
        "manifests": {
            "matched": int(manifest is not None),
            "files": [{"path": manifest}] if manifest is not None else [],
        },
    }
    facts = {
        name: _fact(loader, current_task, name, variables)
        for name in current_task["set_fact"]
    }
    variables.update(facts)
    variables.update({
        "splunk_target_version": target_version,
        "splunk_install": manifest is None,
        "first_run": first_run,
    })
    upgrade_task = _task(loader, "get_facts.yml", "Setting upgrade fact")
    facts["splunk_target_version"] = target_version
    facts["splunk_upgrade"] = _fact(loader, upgrade_task, "splunk_upgrade", variables)
    return facts


@pytest.mark.parametrize(
    "version,build_hash,expected_upgrade",
    [
        ("10.7.0.0", "6da82bdc00cf", False),
        ("10.8.0.0", "6da82bdc00cf", True),
        ("10.7.0.0", "abcdef123456", True),
    ],
)
def test_upgrade_uses_version_and_build_values(version, build_hash, expected_upgrade):
    facts = _version_facts(version, build_hash)
    assert facts["splunk_upgrade"] is expected_upgrade
    assert facts["splunk_current_version"] == "10.7.0.0"
    assert facts["splunk_target_version"] == version
    assert facts["splunk_current_build_hash"] == "6da82bdc00cf"
    assert facts["splunk_target_build_hash"] == build_hash
    assert all(isinstance(facts[name], str) for name in (
        "splunk_current_version", "splunk_target_version",
        "splunk_current_build_hash", "splunk_target_build_hash",
    ))


def test_fresh_install_does_not_upgrade():
    facts = _version_facts("10.7.0.0", "6da82bdc00cf", manifest=None, first_run=True)
    assert facts["splunk_current_version"] == "0"
    assert facts["splunk_current_build_hash"] == "0"
    assert facts["splunk_upgrade"] is False


@pytest.mark.parametrize(
    "target_version,expected",
    [("9.3.0", False), ("9.4.0", True), ("10.7.0.0", True)],
)
def test_preinstall_uses_full_target_version(target_version, expected):
    loader = DataLoader()
    preinstall_task = _task(loader, "get_facts.yml", "Determine if Splunk has preinstall checks")
    assert _fact(loader, preinstall_task, "splunk_preinstall", {
        "splunk_target_version": target_version,
    }) is expected
