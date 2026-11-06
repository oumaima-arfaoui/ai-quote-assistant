import time
from pathlib import Path

from database import init_db, list_requests, save_request
from extract import chain, compute_missing
from qualify import completeness_score, priority
from reply import draft_reply
from schema import QuoteRequest

extract_with_retry = chain.with_retry(stop_after_attempt=3)


def safe_draft_reply(record, attempts: int = 3):
    """Draft reply with retries. Returns None if every attempt fails (the professional writes it by hand)."""
    for attempt in range(attempts):
        try:
            return draft_reply(record)
        except Exception:
            if attempt < attempts - 1:
                time.sleep(1 + attempt)
    return None


def get_status(record) -> str:
    if not record.is_quote_request:
        return "hors demande"
    if record.missing_fields:
        return "à compléter"
    return "en cours de traitement"


def process_text(source_name: str, text: str) -> str:
    if not text.strip():
        raise ValueError("Message vide.")

    try:
        record = extract_with_retry.invoke({"request_text": text})
    except Exception:
        # extraction failed after 3 attempts: keep the message for manual review
        record = QuoteRequest(description=text.strip()[:500])
        record.missing_fields = compute_missing(record)
        status = "à vérifier"
        score = completeness_score(record)
        prio = priority(record)
        save_request(source_name, text, record.model_dump_json(), None, status, score, prio)
        return f"{status} | {score}% | priorité {prio} (l'analyse automatique a échoué)"

    record.missing_fields = compute_missing(record)

    reply = safe_draft_reply(record) if record.is_quote_request else None
    status = get_status(record)
    score = completeness_score(record)
    prio = priority(record)

    save_request(source_name, text, record.model_dump_json(), reply, status, score, prio)
    return f"{status} | {score}% | priorité {prio}"


def process(path: Path) -> str:
    return process_text(path.name, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    init_db()
    for path in sorted(Path("data/requests").glob("*.txt")):
        print(f"{path.name} -> {process(path)}")

    print("\nDemandes classées par priorité :")
    for row in list_requests():
        print(f"  {row['priority']:<8} | {row['completeness']:>3}% | {row['source_file']:<24} | {row['status']}")