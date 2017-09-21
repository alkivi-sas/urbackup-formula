# -*- coding: utf-8 -*-
'''
Manage Urbackup Settings
'''

# Import Python libs
from __future__ import absolute_import
import logging

# Import salt libs
import salt.utils
from salt.exceptions import *

log = logging.getLogger(__name__)

def __virtual__():
    '''
    Only load if urbackup is available
    '''
    return 'urbackup_group' if 'urbackup.add_group' in __salt__ else False


def present(name):
    '''
    Ensure the group is present
    '''
    ret = {'name': name, 'result': True, 'comment': '', 'changes': {}}

    group = __salt__['urbackup.get_group'](name)

    if not group:
        if __opts__['test']:
            ret['comment'] = 'Group {0} will be created.'.format(name)
            ret['result'] = None
            return ret

        ok = __salt__['urbackup.add_group'](name)

        if ok:
            ret['comment'] = 'Created group {0}'.format(name)
        else:
            ret['result'] = False
            ret['comment'] = 'Failed to create group {0}.'.format(name)
    else:
        ret['comment'] = 'Group {0} already exists'.format(name)

    return ret
