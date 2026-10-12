# -*- coding: utf-8 -*-
from pyrevit import script

_STATE_KEY = 'grid_decision_manager_v2'

def save_session_state(data):
    script.set_envvar(_STATE_KEY, data)

def load_session_state():
    data = script.get_envvar(_STATE_KEY)
    if isinstance(data, dict):
        return data
    return {}

def build_summary_text(data):
    return '\n'.join(['{}: {}'.format(k, v) for k, v in sorted(data.items())])
