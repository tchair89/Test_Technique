from .common import get_table, now

def handler(event, context):
    error = event.get("error", {})
    if "upstream" in event and event["upstream"].get("Payload", {}).get("statusCode") == 429:
        message = "UPSTREAM_THROTTLED: retry limit exhausted"
    elif isinstance(error, dict):
        message = str(error.get("Error", "PROCESSING_FAILED"))[:160]
    else:
        message = "PROCESSING_FAILED"
    get_table().update_item(Key={"requestId": event["requestId"]},
        UpdateExpression="SET #s=:s, #e=:e, completedAt=:t",
        ExpressionAttributeNames={"#s": "status", "#e": "error"},
        ExpressionAttributeValues={":s": "FAILED", ":e": message, ":t": now()})
    return {"status": "FAILED", "error": message}
