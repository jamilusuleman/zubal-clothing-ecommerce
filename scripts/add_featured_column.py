import sqlite3

conn = sqlite3.connect("database.db")

cursor = conn.cursor()

cursor.execute("""
ALTER TABLE products
ADD COLUMN featured INTEGER DEFAULT 0
""")

conn.commit()

conn.close()

print("Featured column added successfully")