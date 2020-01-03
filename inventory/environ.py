#!/usr/bin/env python
# Copyright 2018-2020 Splunk
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import print_function

import os
import platform
import json
import argparse
import re
import random
import string
from time import sleep
import socket
import requests
import urllib3
import yaml

urllib3.disable_warnings()

HERE = os.path.dirname(os.path.normpath(__file__))
_PLATFORM = platform.platform().lower()
PLATFORM = "windows" if ("windows" in _PLATFORM or "cygwin" in _PLATFORM) else "linux"
JAVA_VERSION_WHITELIST = frozenset(("oracle:8", "openjdk:8", "openjdk:9", "openjdk:11"))

roleNames = [
    'splunk_cluster_master', # (if it exists, set up indexer clustering)
    'splunk_deployer',
    'splunk_heavy_forwarder',
    'splunk_standalone',
    'splunk_search_head',
    'splunk_indexer',
    'splunk_license_master', # (if it exists, run adding license with a license master)
    'splunk_search_head_captain', # TODO: remove this as we deprecate this role
    'splunk_universal_forwarder',
    'splunk_deployment_server'
]

varPrefix = "SPLUNK_VAR_"
reVarPrefix = r"${varPrefix}(.*)"
envPrefix = "SPLUNK_ROLE_"
reNamePattern = r"${envPrefix}(.*)"

inventory = {
    "_meta": {
        "hostvars": {}
    },
    "all": {
        "hosts": [],
        "children": ["ungrouped"]
    },
    "ungrouped": {
        "hosts": []
    }
}

def getVars(rePattern):
    return {re.match(rePattern, k).group(1).lower():os.environ[k] for k in os.environ
            if re.match(rePattern, k)}

def getSplunkInventory(inventory, reName=r"(.*)_URL"):
    group_information = getVars(reName)
    for group_name in group_information:
        if group_name.lower() in roleNames:
            inventory[group_name] = {}
            hosts = [host.strip() for host in group_information[group_name].split(',')]
            inventory[group_name] = {
                'hosts': list([host.split(':')[0] for host in hosts])
            }
    inventory["all"]["vars"] = getDefaultVars()

    if os.path.isfile("/.dockerenv"):
        if "localhost" not in inventory["all"]["children"]:
            inventory["all"]["hosts"].append("localhost")
        inventory["_meta"]["hostvars"]["localhost"] = loadHostVars(inventory["all"]["vars"],
                                                                   os.uname()[1], PLATFORM)
        inventory["_meta"]["hostvars"]["localhost"]["ansible_connection"] = "local"

def getDefaultVars():
    defaultVars = loadDefaultSplunkVariables()
    overrideEnvironmentVars(defaultVars)

    getIndexerClustering(defaultVars)
    getSearchHeadClustering(defaultVars)
    getMultisite(defaultVars)
    getSplunkWebSSL(defaultVars)
    getDistributedTopology(defaultVars)
    getLicenses(defaultVars)
    defaultVars["splunk"]["role"] = os.environ.get('SPLUNK_ROLE', 'splunk_standalone')
    # Determine DMC settings
    defaultVars["dmc_forwarder_monitoring"] = os.environ.get('DMC_FORWARDER_MONITORING', False)
    defaultVars["dmc_asset_interval"] = os.environ.get('DMC_ASSET_INTERVAL', '3,18,33,48 * * * *')
    # Determine SPLUNK_HOME owner
    defaultVars["splunk_home_ownership_enforcement"] = True
    if os.environ.get("SPLUNK_HOME_OWNERSHIP_ENFORCEMENT", "").lower() == "false":
        defaultVars["splunk_home_ownership_enforcement"] = False
    # Determine password visibility
    defaultVars["hide_password"] = False
    if os.environ.get("HIDE_PASSWORD", "").lower() == "true":
        defaultVars["hide_password"] = True
    # Determine SHC preferred captaincy
    defaultVars["splunk"]["preferred_captaincy"] = True
    if os.environ.get("SPLUNK_PREFERRED_CAPTAINCY", "").lower() == "false":
        defaultVars["splunk"]["preferred_captaincy"] = False
    defaultVars["splunk"]["hostname"] = os.environ.get('SPLUNK_HOSTNAME', socket.getfqdn())
    #When sites are specified, assume multisite
    if "splunk.site" in inventory:
        defaultVars["splunk"]["multisite_replication_factor_origin"] = 1
        defaultVars["splunk"]["multisite_replication_factor_total"] = 1
        defaultVars["splunk"]["multisite_search_factor_origin"] = 1
        defaultVars["splunk"]["multisite_search_factor_total"] = 1

    getJava(defaultVars)
    getSplunkBuild(defaultVars)
    getSplunkbaseToken(defaultVars)
    getSplunkApps(defaultVars)
    getDFS(defaultVars)
    getUFSplunkVariables(defaultVars)
    return defaultVars

def getIndexerClustering(vars_scope):
    """
    Parse and set parameters to configure indexer clustering
    """
    if "idxc" not in vars_scope["splunk"]:
        vars_scope["splunk"]["idxc"] = {}
    idxc_vars = vars_scope["splunk"]["idxc"]
    idxc_vars["label"] = os.environ.get("SPLUNK_IDXC_LABEL", idxc_vars.get("label"))
    idxc_vars["secret"] = os.environ.get("SPLUNK_IDXC_SECRET", idxc_vars.get("secret"))

def getSearchHeadClustering(vars_scope):
    """
    Parse and set parameters to configure search head clustering
    """
    if "shc" not in vars_scope["splunk"]:
        vars_scope["splunk"]["shc"] = {}
    shc_vars = vars_scope["splunk"]["shc"]
    shc_vars["label"] = os.environ.get("SPLUNK_SHC_LABEL", shc_vars.get("label"))
    shc_vars["secret"] = os.environ.get("SPLUNK_SHC_SECRET", shc_vars.get("secret"))

def getMultisite(vars_scope):
    """
    Parse and set parameters to configure multisite
    """
    if "SPLUNK_SITE" in os.environ or "site" in vars_scope["splunk"]:
        splunk_vars = vars_scope["splunk"]
        splunk_vars["site"] = os.environ.get("SPLUNK_SITE", splunk_vars.get("site"))

        all_sites = os.environ.get("SPLUNK_ALL_SITES", splunk_vars.get("all_sites"))
        if all_sites:
            splunk_vars["all_sites"] = all_sites

        multisite_master = os.environ.get("SPLUNK_MULTISITE_MASTER", splunk_vars.get("multisite_master"))
        if multisite_master:
            splunk_vars["multisite_master"] = multisite_master

        splunk_vars["multisite_master_port"] = os.environ.get('SPLUNK_MULTISITE_MASTER_PORT', splunk_vars.get("multisite_master_port", 8089))
        splunk_vars["multisite_replication_factor_origin"] = os.environ.get('SPLUNK_MULTISITE_REPLICATION_FACTOR_ORIGIN', splunk_vars.get("multisite_replication_factor_origin", 1))
        splunk_vars["multisite_replication_factor_total"] = os.environ.get('SPLUNK_MULTISITE_REPLICATION_FACTOR_TOTAL', splunk_vars.get("multisite_replication_factor_total", 1))
        splunk_vars["multisite_search_factor_origin"] = os.environ.get('SPLUNK_MULTISITE_SEARCH_FACTOR_ORIGIN', splunk_vars.get("multisite_search_factor_origin", 1))
        splunk_vars["multisite_search_factor_total"] = os.environ.get('SPLUNK_MULTISITE_SEARCH_FACTOR_TOTAL', splunk_vars.get("multisite_search_factor_total", 1))

def getSplunkWebSSL(vars_scope):
    """
    Parse and set parameters to define Splunk Web accessibility
    """
    # TODO: Split this into its own splunk.http. section
    splunk_vars = vars_scope["splunk"]
    splunk_vars["http_enableSSL"] = bool(os.environ.get('SPLUNK_HTTP_ENABLESSL', splunk_vars.get("http_enableSSL")))
    splunk_vars["http_enableSSL_cert"] = os.environ.get('SPLUNK_HTTP_ENABLESSL_CERT', splunk_vars.get("http_enableSSL_cert"))
    splunk_vars["http_enableSSL_privKey"] = os.environ.get('SPLUNK_HTTP_ENABLESSL_PRIVKEY', splunk_vars.get("http_enableSSL_privKey"))
    splunk_vars["http_enableSSL_privKey_password"] = os.environ.get('SPLUNK_HTTP_ENABLESSL_PRIVKEY_PASSWORD', splunk_vars.get("http_enableSSL_privKey_password"))
    splunk_vars["http_port"] = int(os.environ.get('SPLUNK_HTTP_PORT', splunk_vars.get("http_port")))

def getDistributedTopology(vars_scope):
    """
    Parse and set parameters to define topology if this is a distributed environment
    """
    vars_scope["splunk"]["license_master_included"] = bool(os.environ.get("SPLUNK_LICENSE_MASTER_URL"))
    vars_scope["splunk"]["deployer_included"] = bool(os.environ.get("SPLUNK_DEPLOYER_URL"))
    vars_scope["splunk"]["indexer_cluster"] = bool(os.environ.get("SPLUNK_CLUSTER_MASTER_URL"))
    vars_scope["splunk"]["search_head_cluster"] = bool(os.environ.get("SPLUNK_SEARCH_HEAD_CAPTAIN_URL"))
    vars_scope["splunk"]["search_head_cluster_url"] = os.environ.get("SPLUNK_SEARCH_HEAD_CAPTAIN_URL")

def getLicenses(vars_scope):
    """
    Determine the location of Splunk licenses to install at start-up time
    """
    # Need to provide some file value (does not have to exist). The task will automatically skip over if the file is not found. Otherwise, will throw an error if no file is specified.
    vars_scope["splunk"]["license_uri"] = os.environ.get("SPLUNK_LICENSE_URI", "splunk.lic")
    vars_scope["splunk"]["wildcard_license"] = False
    if vars_scope["splunk"]["license_uri"] and '*' in vars_scope["splunk"]["license_uri"]:
        vars_scope["splunk"]["wildcard_license"] = True
    vars_scope["splunk"]["nfr_license"] = os.environ.get("SPLUNK_NFR_LICENSE", "/tmp/nfr_enterprise.lic")
    vars_scope["splunk"]["ignore_license"] = bool(os.environ.get("SPLUNK_IGNORE_LICENSE"))
    vars_scope["splunk"]["license_download_dest"] = os.environ.get("SPLUNK_LICENSE_INSTALL_PATH", "/tmp/splunk.lic")

def getJava(vars_scope):
    """
    Parse and set Java installation parameters
    """
    vars_scope["java_version"] = None
    vars_scope["java_download_url"] = None
    vars_scope["java_update_version"] = None
    java_version = os.environ.get("JAVA_VERSION")
    if not java_version:
        return
    java_version = java_version.lower()
    if java_version not in JAVA_VERSION_WHITELIST:
        raise Exception("Invalid Java version supplied, supported versions are: {}".format(JAVA_VERSION_WHITELIST))
    vars_scope["java_version"] = java_version
    # TODO: We can probably DRY this up
    if java_version == "oracle:8":
        vars_scope["java_download_url"] = os.environ.get("JAVA_DOWNLOAD_URL", "https://download.oracle.com/otn-pub/java/jdk/8u141-b15/336fa29ff2bb4ef291e347e091f7f4a7/jdk-8u141-linux-x64.tar.gz")
        try:
            vars_scope["java_update_version"] = re.search(r"jdk-8u(\d+)-linux-x64.tar.gz", vars_scope["java_download_url"]).group(1)
        except:
            raise Exception("Invalid Java download URL format")
    elif java_version == "openjdk:11":
        vars_scope["java_download_url"] = os.environ.get("JAVA_DOWNLOAD_URL", "https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_linux-x64_bin.tar.gz")
        try:
            vars_scope["java_update_version"] = re.search(r"openjdk-(\d+\.\d+\.\d+)_linux-x64_bin.tar.gz", vars_scope["java_download_url"]).group(1)
        except:
            raise Exception("Invalid Java download URL format")

def getSplunkBuild(vars_scope):
    """
    Determine the location of the Splunk build
    """
    vars_scope["splunk"]["build_location"] = os.environ.get("SPLUNK_BUILD_URL", vars_scope["splunk"].get("build_location"))
    vars_scope["splunk"]["build_remote_src"] = False
    if vars_scope["splunk"]["build_location"] and vars_scope["splunk"]["build_location"].startswith("http"):
        vars_scope["splunk"]["build_remote_src"] = True

def getSplunkbaseToken(vars_scope):
    """
    Authenticate to SplunkBase and modify the variable scope in-place to utilize temporary session token  
    """
    splunkbase_username = os.environ.get("SPLUNKBASE_USERNAME", vars_scope.get("splunkbase_username"))
    splunkbase_password = os.environ.get("SPLUNKBASE_PASSWORD", vars_scope.get("splunkbase_password"))
    if splunkbase_username and splunkbase_password:
        resp = requests.post("https://splunkbase.splunk.com/api/account:login/",
                             data={"username": splunkbase_username, "password": splunkbase_password})
        if resp.status_code != 200:
            raise Exception("Invalid Splunkbase credentials - will not download apps from Splunkbase")
        output = resp.content
        splunkbase_token = re.search("<id>(.*)</id>", output, re.IGNORECASE)
        vars_scope["splunkbase_token"] = splunkbase_token.group(1) if splunkbase_token else None

def getSplunkApps(vars_scope):
    """
    Determine the set of Splunk apps to install as union of defaults.yml and environment variables
    """
    appSet = set()
    if not "apps_location" in vars_scope["splunk"]:
        vars_scope["splunk"]["apps_location"] = []
    # From default.yml
    elif type(vars_scope["splunk"]["apps_location"]) == str:
        appSet.update(vars_scope["splunk"]["apps_location"].split(","))
    elif type(vars_scope["splunk"]["apps_location"]) == list:
        appSet.update(vars_scope["splunk"]["apps_location"])
    # From environment variables
    apps = os.environ.get("SPLUNK_APPS_URL")
    if apps:
        appSet.update(apps.split(","))
    vars_scope["splunk"]["apps_location"] = list(appSet)

def overrideEnvironmentVars(vars_scope):
    vars_scope["splunk"]["user"] = os.environ.get("SPLUNK_USER", vars_scope["splunk"]["user"])
    vars_scope["splunk"]["group"] = os.environ.get("SPLUNK_GROUP", vars_scope["splunk"]["group"])
    vars_scope["ansible_pre_tasks"] = os.environ.get("SPLUNK_ANSIBLE_PRE_TASKS", vars_scope["ansible_pre_tasks"])
    vars_scope["ansible_post_tasks"] = os.environ.get("SPLUNK_ANSIBLE_POST_TASKS", vars_scope["ansible_post_tasks"])
    vars_scope["cert_prefix"] = os.environ.get("SPLUNK_CERT_PREFIX", vars_scope.get("cert_prefix", "https"))
    vars_scope["splunk"]["opt"] = os.environ.get('SPLUNK_OPT', vars_scope["splunk"]["opt"])
    vars_scope["splunk"]["home"] = os.environ.get('SPLUNK_HOME', vars_scope["splunk"]["home"])
    vars_scope["splunk"]["exec"] = os.environ.get('SPLUNK_EXEC', vars_scope["splunk"]["exec"])
    vars_scope["splunk"]["pid"] = os.environ.get('SPLUNK_PID', vars_scope["splunk"]["pid"])
    vars_scope["splunk"]["root_endpoint"] = os.environ.get('SPLUNK_ROOT_ENDPOINT', vars_scope["splunk"]["root_endpoint"])
    vars_scope["splunk"]["password"] = os.environ.get('SPLUNK_PASSWORD', vars_scope["splunk"]["password"])
    vars_scope["splunk"]["svc_port"] = os.environ.get('SPLUNK_SVC_PORT', vars_scope["splunk"]["svc_port"])
    vars_scope["splunk"]["s2s"]["port"] = int(os.environ.get('SPLUNK_S2S_PORT', vars_scope["splunk"]["s2s"]["port"]))
    vars_scope["splunk"]["secret"] = os.environ.get('SPLUNK_SECRET', vars_scope["splunk"]["secret"])
    vars_scope["splunk"]["hec_token"] = os.environ.get('SPLUNK_HEC_TOKEN', vars_scope["splunk"]["hec_token"])
    vars_scope["splunk"]["enable_service"] = os.environ.get('SPLUNK_ENABLE_SERVICE', vars_scope["splunk"]["enable_service"])
    vars_scope["splunk"]["service_name"] = os.environ.get('SPLUNK_SERVICE_NAME', vars_scope["splunk"]["service_name"])
    vars_scope["splunk"]["allow_upgrade"] = os.environ.get('SPLUNK_ALLOW_UPGRADE', vars_scope["splunk"]["allow_upgrade"])
    vars_scope["splunk"]["build_location"] = os.environ.get('SPLUNK_INSTALLER', vars_scope["splunk"]["build_location"])

def getDFS(vars_scope):
    """
    Parse and set parameters to configure Data Fabric Search
    """
    if "dfs" not in vars_scope["splunk"]:
        vars_scope["splunk"]["dfs"] = {}
    dfs_vars = vars_scope["splunk"]["dfs"]
    dfs_vars["enable"] = bool(os.environ.get("SPLUNK_ENABLE_DFS", dfs_vars.get("enable")))
    dfs_vars["dfw_num_slots"] = int(os.environ.get("SPLUNK_DFW_NUM_SLOTS", dfs_vars.get("dfw_num_slots", 10)))
    dfs_vars["dfc_num_slots"] = int(os.environ.get("SPLUNK_DFC_NUM_SLOTS", dfs_vars.get("dfc_num_slots", 4)))
    dfs_vars["dfw_num_slots_enabled"] = bool(os.environ.get('SPLUNK_DFW_NUM_SLOTS_ENABLED', dfs_vars.get("dfw_num_slots_enabled")))
    dfs_vars["spark_master_host"] = os.environ.get("SPARK_MASTER_HOST", dfs_vars.get("spark_master_host", "127.0.0.1"))
    dfs_vars["spark_master_webui_port"] = int(os.environ.get("SPARK_MASTER_WEBUI_PORT", dfs_vars.get("spark_master_webui_port", 8080)))

def convert_path_windows_to_nix(filepath):
    """
    Normalize all filepaths to Unix-style pathing 
    """
    if filepath.startswith("C:"):
        filepath = re.sub(r"\\+", "/", filepath.lstrip("C:"))
        return filepath

def getUFSplunkVariables(vars_scope):
    """
    Set or override specific environment variables for universal forwarders
    """
    if os.environ.get("SPLUNK_DEPLOYMENT_SERVER"):
        vars_scope["splunk"]["deployment_server"] = os.environ.get("SPLUNK_DEPLOYMENT_SERVER")
    if os.environ.get("SPLUNK_ADD"):
        vars_scope["splunk"]["add"] = os.environ.get("SPLUNK_ADD").split(",")
    if os.environ.get("SPLUNK_BEFORE_START_CMD"):
        vars_scope["splunk"]["before_start_cmd"] = os.environ.get("SPLUNK_BEFORE_START_CMD").split(",")
    if os.environ.get("SPLUNK_CMD"):
        vars_scope["splunk"]["cmd"] = os.environ.get("SPLUNK_CMD").split(",")

def getRandomString():
    char_set = string.ascii_uppercase + string.digits
    return ''.join(random.sample(char_set * 6, 6))

def merge_dict(dict1, dict2, path=None):
    if path is None: path = []
    for key in dict2:
        if key in dict1:
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                merge_dict(dict1[key], dict2[key], path + [str(key)])
            else:
                dict1[key] = dict2[key]
        else:
            dict1[key] = dict2[key]
    return dict1

def mergeDefaultSplunkVariables(vars_scope, url):
    url = url.strip()
    if not url or len(url) == 0:
        return vars_scope
    if url.lower().startswith(('http://', 'https://')):
        headers = None
        if "headers" in vars_scope['config']['env'] and vars_scope['config']['env']['headers'] != None and len(vars_scope['config']['env']['headers']) > 0:
            headers = vars_scope['config']['env']['headers']

        max_retries = int(os.environ.get('SPLUNK_DEFAULTS_HTTP_MAX_RETRIES', vars_scope["config"]["max_retries"]))
        max_delay = int(os.environ.get('SPLUNK_DEFAULTS_HTTP_MAX_DELAY', vars_scope["config"]["max_delay"]))
        max_timeout = int(os.environ.get('SPLUNK_DEFAULTS_HTTP_MAX_TIMEOUT', vars_scope["config"]["max_timeout"]))
        verify = bool(os.environ.get('SPLUNK_DEFAULTS_HTTPS_VERIFY', vars_scope["config"]["env"]["verify"]))
        unlimited_retries = (max_retries == -1)
        current_retry = 0
        while True:
            try:
                response = requests.get(url.format(platform=PLATFORM), headers=headers, timeout=max_timeout, verify=verify)
                response.raise_for_status()
                vars_scope = merge_dict(vars_scope, yaml.load(response.content, Loader=yaml.Loader))
                break
            except Exception as e:
                if unlimited_retries or current_retry < max_retries:
                    current_retry += 1
                    print('URL request #{0} failed, sleeping {1} seconds and retrying'.format(current_retry, max_delay))
                    sleep(max_delay)
                else:
                    raise e
        return vars_scope
    if url.lower().startswith('file://'):
        url = url[7:]
    with open(url, 'r') as file:
        file_content = file.read()
        vars_scope = merge_dict(vars_scope, yaml.load(file_content, Loader=yaml.Loader))
    return vars_scope

def loadDefaultSplunkVariables():
    '''
    This method accepts a url argument, but that argument can be None. If it is None, then we load from a file
    In this way, we manage two different methods of loading the default file (which contains potentially sentive
    information
    '''
    loaded_yaml = {}
    ### Load the splunk defaults shipped with splunk-ansible
    if os.environ.get("SPLUNK_ROLE", None) == "splunk_universal_forwarder":
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "splunkforwarder_defaults_{platform}.yml".format(platform=PLATFORM)), 'r') as yaml_file:
            loaded_yaml = yaml.load(yaml_file, Loader=yaml.Loader)
    else:
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "splunk_defaults_{platform}.yml".format(platform=PLATFORM)), 'r') as yaml_file:
            loaded_yaml = yaml.load(yaml_file, Loader=yaml.Loader)

    ### Load the defaults for the environment
    if "config" in loaded_yaml and loaded_yaml["config"] is not None and "baked" in loaded_yaml["config"]:
        for f in loaded_yaml["config"]["baked"].split(','):
            full_path = os.path.join(loaded_yaml["config"]["defaults_dir"], f.strip())
            if os.path.exists(full_path):
                with open(full_path, 'r') as file:
                    file_content = file.read()
                    loaded_yaml = merge_dict(loaded_yaml, yaml.load(file_content, Loader=yaml.Loader))

    if "config" in loaded_yaml and loaded_yaml["config"] is not None and "env" in loaded_yaml["config"] and loaded_yaml["config"]["env"] is not None and "var" in loaded_yaml["config"]["env"] and loaded_yaml["config"]["env"]["var"] is not None and len(loaded_yaml["config"]["env"]["var"]) > 0:
        urls = os.environ.get(loaded_yaml["config"]["env"]["var"], "")
        for url in urls.split(','):
            loaded_yaml = mergeDefaultSplunkVariables(loaded_yaml, url)
    return loaded_yaml

def loadHostVars(defaults, hostname=None, platform="linux"):
    loaded_yaml = {}
    if hostname == None:
        return loaded_yaml

    url = None
    if "config" in defaults and defaults["config"] is not None and "host" in defaults["config"] and defaults["config"]["host"] is not None and "url" in defaults['config']['host'] and defaults['config']['host']['url'] is not None and len(defaults['config']['host']['url'].strip()) > 0:
        url = defaults['config']['host']['url'].strip()
        headers = None
        if "headers" in defaults['config']['host'] and defaults['config']['host']['headers'] != None and len(defaults['config']['host']['headers']) > 0:
            headers = defaults['config']['host']['headers']

        max_retries = int(os.environ.get('SPLUNK_DEFAULTS_HTTP_MAX_RETRIES', defaults["config"]["max_retries"]))
        max_delay = int(os.environ.get('SPLUNK_DEFAULTS_HTTP_MAX_DELAY', defaults["config"]["max_delay"]))
        max_timeout = int(os.environ.get('SPLUNK_DEFAULTS_HTTP_MAX_TIMEOUT', defaults["config"]["max_timeout"]))
        verify = bool(os.environ.get('SPLUNK_DEFAULTS_HTTPS_VERIFY', defaults["config"]["host"]["verify"]))
        unlimited_retries = (max_retries == -1)
        current_retry = 0
        while True:
            try:
                response = requests.get(url.format(hostname=hostname, platform=platform), headers=headers, timeout=max_timeout, verify=verify)
                response.raise_for_status()
                loaded_yaml = merge_dict(loaded_yaml, yaml.load(response.content, Loader=yaml.Loader))
                break
            except Exception as e:
                if unlimited_retries or current_retry < max_retries:
                    current_retry += 1
                    print('URL request #{0} failed, sleeping {1} seconds and retrying'.format(current_retry, max_delay) + str(e))
                    sleep(max_delay)
                else:
                    raise e
    return loaded_yaml

def obfuscate_vars(inventory):
    """
    Remove sensitive variables when dumping inventory out to stdout or file
    """
    stars = "*"*14
    splunkVars = inventory.get("all", {}).get("vars", {}).get("splunk", {})
    if splunkVars.get("password"):
        splunkVars["password"] = stars
    if splunkVars.get("shc") and splunkVars["shc"].get("secret"):
        splunkVars["shc"]["secret"] = stars
    if splunkVars.get("idxc") and splunkVars["idxc"].get("secret"):
        splunkVars["idxc"]["secret"] = stars
    if splunkVars.get("smartstore") and splunkVars["smartstore"].get("index"):
        splunkIndexes = splunkVars["smartstore"]["index"]
        for idx in range(0, len(splunkIndexes)):
            if splunkIndexes[idx].get("s3"):
                if splunkIndexes[idx]["s3"].get("access_key"):
                    splunkIndexes[idx]["s3"]["access_key"] = stars
                if splunkIndexes[idx]["s3"].get("secret_key"):
                    splunkIndexes[idx]["s3"]["secret_key"] = stars
    return inventory

def create_parser():
    parser = argparse.ArgumentParser(description='Return Ansible inventory defined in the environment.')
    parser.add_argument('--list', action='store_true', default=True, help='List all hosts (default: True)')
    parser.add_argument('--host', action='store', help='Only get information for a specific host.')
    parser.add_argument('--write-to-file', action='store_true', default=False, help='Write to file for debugging')
    parser.add_argument('--write-to-stdout', action='store_true', default=False, help='create a default.yml file shown on stdout from current vars')
    return parser

def prep_for_yaml_out(inventory):
    inventory_to_dump = inventory["all"]["vars"]

    keys_to_del = ["docker_version",
                   "ansible_ssh_user",
                   "delay_num",
                   "apps_location",
                   "build_location",
                   "build_remote_src",
                   "deployer_included",
                   "upgrade",
                   "role",
                   "search_head_cluster",
                   "indexer_cluster",
                   "license_master_included",
                   "preferred_captaincy",
                   "license_uri"]
    for key in keys_to_del:
        if key in inventory_to_dump:
            del inventory_to_dump[key]
        if key in inventory_to_dump["splunk"]:
            del inventory_to_dump["splunk"][key]
        if key in inventory_to_dump["splunk"]["app_paths"]:
            del inventory_to_dump["splunk"]["app_paths"][key]
        if key in inventory_to_dump["splunk"]["shc"]:
            del inventory_to_dump["splunk"]["shc"][key]
        if key in inventory_to_dump["splunk"]["idxc"]:
            del inventory_to_dump["splunk"]["idxc"][key]
    #remove extra stuff when we know it's the forwarder
    if inventory_to_dump["splunk"]["home"] == "/opt/splunkforwarder":
        del inventory_to_dump["splunk"]["idxc"]
        del inventory_to_dump["splunk"]["shc"]
    return inventory_to_dump

def main():
    """
    Primary entrypoint to dynamic inventory script
    """
    parser = create_parser()
    args = parser.parse_args()

    getSplunkInventory(inventory)
    if args.write_to_file:
        with open(os.path.join("/opt/container_artifact", "ansible_inventory.json"), "w") as outfile:
            json.dump(obfuscate_vars(inventory), outfile, sort_keys=True, indent=4, ensure_ascii=False)
    elif args.write_to_stdout:
        #remove keys we don't want to print
        inventory_to_dump = prep_for_yaml_out(inventory)
        print("---")
        print(yaml.dump(inventory_to_dump, default_flow_style=False))
    else:
        print(json.dumps(inventory))


if __name__ == "__main__":
    main()
