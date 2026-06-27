import sqlite3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Connect to SQLite
sqlite_conn = sqlite3.connect("database.db")
sqlite_cursor = sqlite_conn.cursor()

# Connect to PostgreSQL
pg_conn = psycopg2.connect(DATABASE_URL)
pg_cursor = pg_conn.cursor()


def migrate_table(sqlite_table, postgres_table, columns):
    print(f"Migrating {sqlite_table}...")

    sqlite_cursor.execute(f"SELECT {', '.join(columns)} FROM {sqlite_table}")
    rows = sqlite_cursor.fetchall()

    placeholders = ", ".join(["%s"] * len(columns))

    insert_query = f"""
        INSERT INTO {postgres_table}
        ({', '.join(columns)})
        VALUES ({placeholders})
    """

    for row in rows:
        pg_cursor.execute(insert_query, row)

    pg_conn.commit()

    print(f"✓ {len(rows)} records migrated.")


# PRODUCTS
migrate_table(
    "products",
    "products",
    [
        "name",
        "category",
        "price",
        "description",
        "image",
        "gallery_image",
        "stock",
        "featured",
    ],
)

# ORDERS
migrate_table(
    "orders",
    "orders",
    [
        "customer_name",
        "phone",
        "address",
        "products",
        "total",
        "status",
    ],
)

# CUSTOMERS
migrate_table(
    "customers",
    "customers",
    [
        "fullname",
        "email",
        "password",
    ],
)

# REVIEWS
migrate_table(
    "reviews",
    "reviews",
    [
        "customer_name",
        "product_id",
        "rating",
        "comment",
    ],
)

sqlite_conn.close()
pg_conn.close()

print("\nMigration completed successfully!")