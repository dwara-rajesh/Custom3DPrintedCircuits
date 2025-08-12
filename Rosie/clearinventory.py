"""
This script refreshes the inventory. RUN after restocking and placing all the components in their respected grids.
"""
import json

inventory_file_path = r"C:\git\ADML\Automated Circuit Printing and Assembly\Summer2025\inventory.json"

with open(inventory_file_path, 'r') as f:
    data = json.load(f)
for key, _ in data.items():
    data[key] = []

with open(inventory_file_path, 'w') as f:
    data = json.dump(data,f)