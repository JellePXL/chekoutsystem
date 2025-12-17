import sqlite3

# ==========================================
# 1. EDIT YOUR PRICES HERE
# ==========================================
# Make sure the names match your labels.txt EXACTLY (case sensitive).
# Format: "Item Name": Price

MY_PRICES = {
    "Appel": 0.75,
    "Avocado": 1.49,    
    "Banaan": 0.89,
    # Add all your labels here...
}

# ==========================================
# 2. GENERATE DATABASE
# ==========================================

print("--- Starting Database Generation ---")

conn = sqlite3.connect('prices.db')
cursor = conn.cursor()

# Wipe old data cleanly (No OS module needed)
cursor.execute("DROP TABLE IF EXISTS products")

# Create table
cursor.execute('''
    CREATE TABLE products (
        item_name TEXT PRIMARY KEY,
        price REAL
    )
''')

# Insert the prices from your list above
count = 0
for item, price in MY_PRICES.items():
    cursor.execute('INSERT INTO products (item_name, price) VALUES (?, ?)', (item, price))
    print(f"   Added: {item} -> €{price:.2f}")
    count += 1

conn.commit()
conn.close()

print("------------------------------------")
print(f"✅ Done! 'prices.db' created with {count} items.")