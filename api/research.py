import json

from api.service import run_research_payload


def handler(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
        query = body.get("query", "")
        result = run_research_payload(query)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result),
        }
    except Exception as exc:
        return {
            "statusCode": 400 if isinstance(exc, ValueError) else 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(exc)}),
        }
