from catalog import load_catalog

for item_id, item in load_catalog().items():
    print(f"{item_id} | {item.service_name} | {item.unit} | {item.conditions or '-'}")