from datetime import datetime, timezone
import pytz

def test_expr(expiry):
    def _utcnow():
        return datetime.now(timezone.utc)
        
    try:
        res = expiry and _utcnow() > expiry.replace(tzinfo=timezone.utc) if expiry.tzinfo is None else expiry
        print(f"Result for {expiry}: {res}")
    except Exception as e:
        print(f"Error for {expiry}: {e}")

test_expr(None)
test_expr(datetime.now())
test_expr(datetime.now(timezone.utc))
