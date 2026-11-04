import csv
from pathlib import Path

from pydantic import BaseModel

CATALOG_PATH = Path("data/company/catalog.csv")


class CatalogItem(BaseModel):
    item_id: str
    service_name: str
    category: str
    unit: str
    unit_price_ht_eur: float
    vat_rate_percent: float
    conditions: str = ""


def load_catalog() -> dict[str, CatalogItem]:
    items = {}
    with open(CATALOG_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            item = CatalogItem(**row)
            items[item.item_id] = item
    return items


if __name__ == "__main__":
    catalog = load_catalog()
    print(f"{len(catalog)} prestations chargées")

    item = catalog["PLOMB-003"]
    print(item)
    ttc = round(item.unit_price_ht_eur * (1 + item.vat_rate_percent / 100), 2)
    print(f"Prix HT : {item.unit_price_ht_eur} EUR | TTC : {ttc} EUR")
    