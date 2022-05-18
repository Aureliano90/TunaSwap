from cerberus import Validator
from src.consts import *

msg_validator = Validator({}, require_all=True, allow_unknown=True)

send_schema = {
    'send': {
        'type': 'dict',
        'schema': {
            'contract': {'type': 'string'},
            'amount': {'type': 'string'},
            'msg': {'type': 'string'}
        }
    }
}

swap_schema = {
    'swap': {
        'type': 'dict',
        'schema': {
            'offer_asset': {
                'type': 'dict',
                'schema': {
                    'info': {'type': 'string'},
                    'amount': {'type': 'string'}
                }
            }
        }
    }
}

swap_operations_schema = {
    'execute_swap_operations': {
        'type': 'dict',
        'schema': {
            'operations': {
                'type': 'list',
                'schema': {
                    'type': 'dict',
                    'valuesrules': {'type': 'dict'},
                    'keysrules': {
                        'type': 'string',
                        'allowed': list(dexes)
                    }
                }
            }
        }
    }
}

