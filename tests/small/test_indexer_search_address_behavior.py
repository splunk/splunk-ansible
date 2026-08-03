"""Executable ownership tests for stable indexer search-address registration."""

import configparser
import grp
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import textwrap

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_FILE = (
    REPO_ROOT
    / "roles"
    / "splunk_common"
    / "tasks"
    / "configure_indexer_search_address_prestart.yml"
)
MARKER_NAME = ".splunk-ansible-register-search-address-managed"


class SearchAddressHarness:
    """Run the real Ansible task file against an isolated fake Splunk home."""

    def __init__(self, tmp_path):
        self.home = tmp_path / "splunk"
        self.local = self.home / "etc" / "system" / "local"
        self.local.mkdir(parents=True)
        self.server_conf = self.local / "server.conf"
        self.marker = self.home / "etc" / MARKER_NAME
        self.fake_splunk = tmp_path / "fake-splunk"
        self.playbook = tmp_path / "playbook.yml"
        self.ansible_tmp = tmp_path / "ansible-tmp"
        self.ansible_tmp.mkdir()
        self.user = pwd.getpwuid(os.getuid()).pw_name
        self.group = grp.getgrgid(os.getgid()).gr_name
        self._write_fake_splunk()

    def _write_fake_splunk(self):
        source = textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import configparser
            from pathlib import Path
            import sys

            expected = ["btool", "server", "list", "clustering", "--no-log"]
            if sys.argv[1:] != expected:
                raise SystemExit("unexpected fake Splunk arguments")

            parser = configparser.ConfigParser()
            parser.read(Path({str(self.server_conf)!r}))
            print("[clustering]")
            if parser.has_option("clustering", "register_search_address"):
                value = parser.get("clustering", "register_search_address")
                print("register_search_address = " + value)
            """
        )
        self.fake_splunk.write_text(source, encoding="utf-8")
        self.fake_splunk.chmod(self.fake_splunk.stat().st_mode | stat.S_IXUSR)

    def set_address(self, value):
        parser = configparser.ConfigParser()
        parser["clustering"] = {"register_search_address": value}
        with self.server_conf.open("w", encoding="utf-8") as output:
            parser.write(output)

    def get_address(self):
        parser = configparser.ConfigParser()
        parser.read(self.server_conf)
        if not parser.has_option("clustering", "register_search_address"):
            return None
        return parser.get("clustering", "register_search_address")

    def run(self, mode, value):
        play = [{
            "hosts": "localhost",
            "connection": "local",
            "gather_facts": False,
            "vars": {
                "splunk": {
                    "home": str(self.home),
                    "exec": str(self.fake_splunk),
                    "user": self.user,
                    "group": self.group,
                    "idxc": {
                        "register_search_address": value,
                        "register_search_address_mode": mode,
                    },
                },
            },
            "tasks": [{"include_tasks": str(TASK_FILE)}],
        }]
        self.playbook.write_text(yaml.safe_dump(play), encoding="utf-8")
        executable = os.environ.get("SHC_ANSIBLE_PLAYBOOK") or shutil.which(
            "ansible-playbook"
        )
        assert executable, "ansible-playbook is required for executable task tests"
        environment = os.environ.copy()
        environment.update({
            "ANSIBLE_LOCAL_TEMP": str(self.ansible_tmp),
            "ANSIBLE_NOCOLOR": "1",
            "ANSIBLE_REMOTE_TEMP": str(self.ansible_tmp),
        })
        result = subprocess.run(
            [executable, "-i", "localhost,", str(self.playbook)],
            cwd=REPO_ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result


def test_auto_preserves_an_unmanaged_customer_value(tmp_path):
    harness = SearchAddressHarness(tmp_path)
    harness.set_address("customer.example")

    harness.run("auto", "generated.example")

    assert harness.get_address() == "customer.example"
    assert not harness.marker.exists()


def test_auto_adopts_empty_configuration_and_absent_removes_owned_value(tmp_path):
    harness = SearchAddressHarness(tmp_path)

    harness.run("auto", "generated.example")

    assert harness.get_address() == "generated.example"
    assert harness.marker.read_text(encoding="utf-8") == "generated.example\n"

    result = harness.run("auto", "generated.example")

    assert "changed=0" in result.stdout

    harness.run("absent", "absent")

    assert harness.get_address() is None
    assert not harness.marker.exists()


def test_absent_preserves_an_unmanaged_customer_value(tmp_path):
    harness = SearchAddressHarness(tmp_path)
    harness.set_address("customer.example")

    harness.run("absent", "absent")

    assert harness.get_address() == "customer.example"
    assert not harness.marker.exists()


def test_explicit_value_overrides_and_records_ownership(tmp_path):
    harness = SearchAddressHarness(tmp_path)
    harness.set_address("customer.example")

    harness.run("explicit", "requested.example")

    assert harness.get_address() == "requested.example"
    assert harness.marker.read_text(encoding="utf-8") == "requested.example\n"


def test_auto_relinquishes_stale_ownership_after_customer_change(tmp_path):
    harness = SearchAddressHarness(tmp_path)
    harness.run("auto", "generated.example")
    harness.set_address("customer.example")

    harness.run("auto", "new-generated.example")

    assert harness.get_address() == "customer.example"
    assert not harness.marker.exists()


def test_absent_preserves_customer_change_after_prior_ownership(tmp_path):
    harness = SearchAddressHarness(tmp_path)
    harness.run("auto", "generated.example")
    harness.set_address("customer.example")

    harness.run("absent", "absent")

    assert harness.get_address() == "customer.example"
    assert not harness.marker.exists()
