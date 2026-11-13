#!/usr/bin/env python
"""Shared helpers for merging and normalizing Splunk configuration."""

from __future__ import absolute_import

import copy
import os

# Each entry under these mappings is replaced whole by the last file declaring it;
# deep merging an entry would concatenate list values such as a user's roles.
REPLACED_ENTRY_PATHS = frozenset([("splunk", "users")])

def merge_dict(dict1, dict2, path=None):
    """
    Merge two dictionaries such that keys in dict2 overwrite those in dict1.

    Preserve mappings when a later YAML section is empty, and merge dictionary
    items from a later list into an existing mapping.
    """
    if path is None:
        path = []
    replace_entries = tuple(path) in REPLACED_ENTRY_PATHS
    for key in dict2:
        if key in dict1 and not replace_entries:
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                merge_dict(dict1[key], dict2[key], path + [str(key)])
            elif tuple(path + [str(key)]) in REPLACED_ENTRY_PATHS and isinstance(dict2[key], list):
                # Keep the list so validation rejects it rather than folding it in
                dict1[key] = dict2[key]
            elif isinstance(dict1[key], list) and isinstance(dict2[key], list):
                dict1[key] += dict2[key]
            elif isinstance(dict1[key], dict) and dict2[key] is None:
                pass
            elif isinstance(dict1[key], dict) and isinstance(dict2[key], list):
                for item in dict2[key]:
                    if isinstance(item, dict):
                        merge_dict(dict1[key], item, path + [str(key)])
            else:
                dict1[key] = dict2[key]
        else:
            dict1[key] = dict2[key]
    return dict1


def normalize_path(path):
    """Return the canonical lexical identity for a configuration directory."""
    return os.path.normcase(os.path.normpath(path))


def normalize_conf_entries(entries, default_directory, file_keys=None):
    """Merge list entries that target the same effective configuration file."""
    if not isinstance(entries, list):
        return entries

    selected_keys = set(file_keys) if file_keys is not None else None
    normalized = []
    entry_positions = {}

    for source_entry in entries:
        entry = copy.deepcopy(source_entry)
        if not isinstance(entry, dict) or not isinstance(entry.get("value"), dict):
            normalized.append(entry)
            continue

        file_key = entry.get("key")
        if file_key is None or (selected_keys is not None and file_key not in selected_keys):
            normalized.append(entry)
            continue

        directory = entry["value"].get("directory") or default_directory
        if not directory:
            normalized.append(entry)
            continue

        identity = (normalize_path(directory), file_key)
        if identity in entry_positions:
            existing_entry = normalized[entry_positions[identity]]
            merge_dict(existing_entry["value"], entry["value"])
            continue

        entry_positions[identity] = len(normalized)
        normalized.append(entry)

    return normalized
