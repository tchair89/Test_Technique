from .common import get_table, now

def handler(event, context):
    upstream = event["upstream"]["Payload"]
    if upstream.get("statusCode") != 200:
        raise ValueError("Unexpected provider status")
    normalized = {"service": event["service"], "operation": event["operation"], "vehicleId": event["parameters"]["vehicleId"], "payload": upstream["data"]}
    get_table().update_item(Key={"requestId": event["requestId"]},
        UpdateExpression="SET #s=:s, #r=:r, completedAt=:t",
        ExpressionAttributeNames={"#s": "status", "#r": "result"},
        ExpressionAttributeValues={":s": "SUCCEEDED", ":r": normalized, ":t": now()})
    return {"status": "SUCCEEDED"}
