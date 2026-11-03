from .common import owner_from_event, response, get_table

def handler(event, context):
    try:
        owner = owner_from_event(event)
    except PermissionError:
        return response(403, {"error": "Unauthorized"})
    request_id = event.get("pathParameters", {}).get("requestId", "")
    item = get_table().get_item(Key={"requestId": request_id}).get("Item")
    if not item or item["owner"] != owner:
        return response(404, {"error": "Request not found"})
    if item["status"] != "SUCCEEDED":
        return response(409, {"requestId": request_id, "status": item["status"], "error": "Result not available"})
    return response(200, {"requestId": request_id, "status": "SUCCEEDED", "data": item["result"]})
