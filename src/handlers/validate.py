from .common import validate

def handler(event, context):
    validate(event)
    return {"valid": True}
