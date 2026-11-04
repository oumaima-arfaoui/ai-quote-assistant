from pathlib import Path
from qualify import completeness_score, priority
from database import init_db, list_requests, save_request
from extract import chain, compute_missing
from reply import draft_reply


def get_status(record) -> str:
    if not record.is_quote_request:
        return "hors demande"
    if record.missing_fields:
        return "à compléter"
    return "en cours de traitement"


def process(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    record = chain.invoke({"request_text": text})
    record.missing_fields = compute_missing(record)

    reply = draft_reply(record) if record.is_quote_request else None
    status = get_status(record)
    score = completeness_score(record)
    prio = priority(record)

    save_request(path.name, text, record.model_dump_json(), reply, status, score, prio)
    return f"{status} | {score}% | priorité {prio}"

if __name__ == "__main__":
    init_db()
    for path in sorted(Path("data/requests").glob("*.txt")):
        print(f"{path.name} -> {process(path)}")

    print("\nDemandes classées par priorité :")
    for row in list_requests():
        print(f"  {row['priority']:<8} | {row['completeness']:>3}% | {row['source_file']:<24} | {row['status']}")