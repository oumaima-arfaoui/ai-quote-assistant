from unittest.mock import patch

import pipeline
from database import get_connection, init_db

init_db()


def reply_fails(record):
    raise RuntimeError("Bedrock indisponible (test)")


text = (
    "Bonjour, je voudrais un devis pour poser un lavabo. Marie Dupont, 06 00 00 00 00, "
    "marie@example.com, 5 rue Test, 31000 Toulouse, disponible en semaine."
)

with patch.object(pipeline, "draft_reply", reply_fails), patch("pipeline.time.sleep"):
    print(pipeline.process_text("test_reply_failure.txt", text))

with get_connection() as conn:
    row = conn.execute(
        "SELECT status, completeness, priority, draft_reply FROM requests WHERE source_file = ?",
        ("test_reply_failure.txt",),
    ).fetchone()
    print(dict(row))
    conn.execute("DELETE FROM requests WHERE source_file = ?", ("test_reply_failure.txt",))