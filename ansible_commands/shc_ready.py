#!/usr/bin/python
'''
Ansible module

This module will be called to wait until SHC is completely setup and 
initial bundle replication has occurred such that user defined 
bundles are safe to push
'''
import time
import json 
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from ansible.module_utils.basic import AnsibleModule

class ShcReady(object):
    def __init__(self, module):
        self.captain_url = module.params["captain_url"]
        self.shc_peers = module.params["shc_peers"]
        self.user = module.params["spl_user"]
        self.password = module.params["spl_pass"]

    def run(self):
        URL = "https://{0}:8089/services/shcluster/status?output_mode=json".format(self.captain_url) 
        online_peers = None 
        resp = requests.get(URL, auth=(self.user, self.password), verify=False).json()
        shc_peers = resp['entry'][0]['content']['peers']
        # Check #1, see if peers are up
        # the comparison will be >= in case play is run after cluster is setup
        if not len(shc_peers.keys()) >= (len(self.shc_peers) + 1): # SH Captain included in list
            raise Exception("SHC failure, setup not complete. Insufficient number of peers online")
        #correct number of peers online
        # Check #2, see if peers are ready to accept bundle
        online_peers = [peer for peer in shc_peers if shc_peers[peer].get('last_conf_replication', None) != "Pending"] 
        if not len(online_peers) >= (len(self.shc_peers) + 1): # SH Captain included in list
            raise Exception("SHC failure, setup not complete. online_peers:{0}".format(online_peers))
        #correct number of peers ready to accept bundle
        return {1:self.captain_url, 2:self.shc_peers, 3: self.user, 4: self.password, 5:online_peers}

def main():
    module = AnsibleModule(
        argument_spec=dict(
            captain_url=dict(required=True, type='str'),
            shc_peers=dict(required=True, type='list'),
            spl_user=dict(required=True, type='str'),
            spl_pass=dict(required=True, type='str')
        )
    )
    shc_ready = ShcReady(module).run()
    res = dict(changed=False, ansible_facts=shc_ready, rc=0)
    module.exit_json(**res)

if __name__ == '__main__':
    main()