#!/usr/bin/env python
"""Ansible filters for Noah's effective Splunk configuration."""

from __future__ import absolute_import

import os
import runpy


SPLUNK_CONFIG_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "inventory", "splunk_config.py"
    )
)
SPLUNK_CONFIG = runpy.run_path(SPLUNK_CONFIG_PATH)
normalize_conf_entries = SPLUNK_CONFIG["normalize_conf_entries"]
normalize_path = SPLUNK_CONFIG["normalize_path"]


class FilterModule(object):
    def filters(self):
        return {
            "normalize_splunk_conf_entries": normalize_conf_entries,
            "normalize_splunk_conf_path": normalize_path,
        }
