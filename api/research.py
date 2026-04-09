import json

def handler(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
        query = body.get("query", "")

        if not query:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Query is required"})
            }

        # ⚠️ heavy import INSIDE handler
        from pipeline.orchestrator import run_research

        result = run_research(query)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "answer": result.final_answer.answer if result.final_answer else None,
                "confidence": result.final_answer.confidence if result.final_answer else None
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }