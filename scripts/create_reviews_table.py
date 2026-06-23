import sqlite3

conn = sqlite3.connect("database.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    customer_name TEXT NOT NULL,

    product_id INTEGER NOT NULL,

    rating INTEGER NOT NULL,

    comment TEXT NOT NULL

)
""")

conn.commit()

conn.close()

print("Reviews table created successfully")