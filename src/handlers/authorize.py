from .common import validate, authorize

def handler(event, context):
    authorize(event.get("owner"), validate(event))
    return {"authorized": True}
