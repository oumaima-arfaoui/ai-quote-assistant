from extract import REQUIRED_FIELDS
from schema import Urgency

TOTAL_CHECKS = len(REQUIRED_FIELDS) + 1  # the 5 fields + work_types


def completeness_score(record) -> int:
    if not record.is_quote_request:
        return 0
    present = TOTAL_CHECKS - len(record.missing_fields)
    return round(100 * present / TOTAL_CHECKS)


def priority(record) -> str:
    if not record.is_quote_request:
        return "aucune"
    if record.urgency == Urgency.URGENT:
        return "haute"
    if completeness_score(record) >= 70:
        return "moyenne"
    return "basse"