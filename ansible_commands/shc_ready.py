#!/usr/bin/python
'''
Ansible module

This module will be called to wait until SHC is completely setup and 
initial bundle replication has occurred such that user defined 
bundles are safe to push
'''

import os
import urllib2
from urllib2 import HTTPError
import urlparse
import re

from ansible.module_utils.basic import AnsibleModule


class ShcReady(object):
    def __init__(self, module):
        self.captain_url = module.params["captain_url"]
        self.shc_peers = module.params["shc_peers"]
        self.user = module.params["spl_user"]
        self.password = module.params["spl_pass"]

    def run(self):
        return {1:self.captain_url, 2:self.shc_peers, 3: self.user, 4: self.password}

def main():
    module = AnsibleModule(
        argument_spec=dict(
            captain_url=dict(required=True, type='str'),
            shc_peers=dict(required=True, type='str'),
            spl_user=dict(required=True, type='str'),
            spl_pass=dict(required=True, type='str')
        )
    )
    shc_ready = ShcReady(module).run()
    res = dict(changed=False, ansible_facts=shc_ready)
    module.exit_json(**res)

if __name__ == '__main__':
    main()
