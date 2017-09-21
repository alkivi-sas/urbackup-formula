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
    return 'urbackup_setting' if 'urbackup.set_global_setting' in __salt__ else False


def present(
        name,
        value):
    '''
    Ensure the setting is present
    '''
    ret = {'name': name, 'result': True, 'comment': '', 'changes': {}}

    setting = __salt__['urbackup.get_global_setting'](name)

    if not setting:
        if __opts__['test']:
            ret['comment'] = 'Setting {0} will be created to {1}.'.format(name, value)
            ret['result'] = None
            return ret

        ok = __salt__['urbackup.set_global_setting'](name, value)

        if ok:
            ret['comment'] = 'Created setting {0} to {1}'.format(name, value)
        else:
            ret['result'] = False
            ret['comment'] = 'Failed to create setting {0} to {1}.'.format(name, value)

    elif str(setting) != str(value):
        if __opts__['test']:
            ret['comment'] = 'Setting {0} will be updated to {1}.'.format(name, value)
            ret['result'] = None
            return ret

        ok = __salt__['urbackup.set_global_setting'](name, value)

        if ok:
            ret['changes']['old'] = setting
            ret['changes']['new'] = value
            ret['comment'] = 'Updated setting {0}'.format(name)
        else:
            ret['result'] = False
            ret['comment'] = 'Failed to update setting {0} to {1}.'.format(name, value)
    else:
        ret['comment'] = 'Setting {0} already set to {1}'.format(name, value)

    return ret
