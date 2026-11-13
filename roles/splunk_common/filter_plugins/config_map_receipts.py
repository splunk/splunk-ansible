#!/usr/bin/env python
"""Ansible filters for reconciling ConfigMap-owned options against their receipt."""

from __future__ import absolute_import


def config_map_dropped_options(previous_stanzas, desired_stanzas):
    """Return the previously recorded options that the desired stanzas no longer set."""
    if not isinstance(previous_stanzas, dict):
        return {}
    if not isinstance(desired_stanzas, dict):
        desired_stanzas = {}

    dropped = {}
    for stanza_name, previous_options in previous_stanzas.items():
        if not isinstance(previous_options, dict):
            continue
        desired_options = desired_stanzas.get(stanza_name)
        if not isinstance(desired_options, dict):
            desired_options = {}
        stale = dict(
            (option, value)
            for option, value in previous_options.items()
            if option not in desired_options
        )
        if stale:
            dropped[stanza_name] = stale
    return dropped


class FilterModule(object):
    def filters(self):
        return {
            "config_map_dropped_options": config_map_dropped_options,
        }
