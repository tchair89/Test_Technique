import os
import uuid
from .common import validate, authorize, owner_from_event, parse_body, response, get_table, now

def handler(event, context):
    try:
        owner = owner_from_event(event)
        payload = validate(parse_body(event))
        authorize(owner, payload)
    except ValueError as exc:
        return response(400, {"error": str(exc)})
    except PermissionError as exc:
        return response(403, {"error": str(exc)})
    request_id = str(uuid.uuid4())
    table = get_table()
    table.put_item(Item={"requestId": request_id, "owner": owner, "status": "PENDING", "createdAt": now()})
    try:
        import boto3
        boto3.client("stepfunctions").start_execution(
            stateMachineArn=os.environ["STATE_MACHINE_ARN"],
            name=request_id,
            input=__import__('json').dumps({"requestId": request_id, "owner": owner, **payload, "attempt": 0}),
        )
    except Exception:
        table.update_item(Key={"requestId": request_id}, UpdateExpression="SET #s=:s, #e=:e",
                          ExpressionAttributeNames={"#s": "status", "#e": "error"},
                          ExpressionAttributeValues={":s": "FAILED", ":e": "Unable to start workflow"})
        return response(503, {"requestId": request_id, "status": "FAILED", "error": "Unable to start workflow"})
    return response(202, {"requestId": request_id, "status": "PENDING"})
