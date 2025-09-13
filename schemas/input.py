INPUT_SCHEMA = {
    'workflow': {
        'type': str,
        'required': False,
        'default': 'custom',
        'constraints': lambda workflow: workflow in [
            'txt2img',
            'custom'
        ]
    },
    'callback': {
        'type': dict,
        'required': False
    },
    'payload': {
        'type': dict,
        'required': True
    }
}
