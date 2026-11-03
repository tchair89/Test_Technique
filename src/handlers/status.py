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
    result = {"requestId": request_id, "status": item["status"]}
    if item["status"] == "FAILED":
        result["error"] = item.get("error", "Processing failed")
    return response(200, result)
