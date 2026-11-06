from pathlib import Path

from extract import chain

for path in sorted(Path("data/requests").glob("*.txt")):
    record = chain.invoke({"request_text": path.read_text(encoding="utf-8")})
    print(f"{path.name:<26} | surface_m2 = {record.surface_m2}")