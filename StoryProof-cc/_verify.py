"""Temporary verification script - delete after use"""
try:
    from backend.main import app
    print("Backend import: OK")
    routes = [r.path for r in app.routes if hasattr(r, "path")]
    print(f"Total routes: {len(routes)}")
    for r in routes:
        print(f"  {r}")
except Exception as e:
    print(f"FAILED: {e}")
