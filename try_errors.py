from unittest.mock import patch

from langchain_core.runnables import RunnableLambda

import pipeline
from database import get_connection, init_db

init_db()

# 1. retry: a function that fails twice, then works
calls = {"n": 0}


def flaky(_):
    calls["n"] += 1
    if calls["n"] < 3:
        raise RuntimeError("erreur temporaire")
    return "ok"


result = RunnableLambda(flaky).with_retry(stop_after_attempt=3, wait_exponential_jitter=False).invoke("x")
print("Retry :", result, "après", calls["n"], "appels")


# 2. fallback: an extraction that always fails
class AlwaysFails:
    def invoke(self, *args, **kwargs):
        raise RuntimeError("Bedrock indisponible (test)")


with patch.object(pipeline, "extract_with_retry", AlwaysFails()):
    print("Fallback :", pipeline.process_text("test_failure.txt", "Bonjour, je voudrais un devis pour peindre ma cuisine."))

with get_connection() as conn:
    row = conn.execute(
        "SELECT status, completeness, priority, draft_reply FROM requests WHERE source_file = ?",
        ("test_failure.txt",),
    ).fetchone()
    print(dict(row))
    conn.execute("DELETE FROM requests WHERE source_file = ?", ("test_failure.txt",))