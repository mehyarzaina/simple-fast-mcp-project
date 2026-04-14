from mcp.server.fastmcp import FastMCP
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

## Initialize FastMCP server
mcp = FastMCP("Cars_DB")

#DB config
conn = psycopg2.connect(
    DB_USER = os.getenv('DB_USER'),
    DB_PASSWORD = os.getenv('DB_PASSWORD'),
    DB_HOST = os.getenv('DB_HOST'),
    DB_PORT = os.getenv('DB_PORT'),
    DB_NAME = os.getenv('DB_NAME'),
    port=5432
)


@mcp.tool()
def count_all_records():
    """Count all records in the database."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM car;")
    return cur.fetchone()[0]


@mcp.tool()
def count_by_make():
    """Count car by make."""
    cur = conn.cursor()
    cur.execute("""
        SELECT car_make, COUNT(*)
        FROM car
        GROUP BY car_make
        ORDER BY COUNT(*) DESC;
    """)
    return cur.fetchall()


@mcp.tool()
def get_first_last_pub_date():
    """Get first and last publish date."""
    cur = conn.cursor()
    cur.execute("""
        SELECT MIN(pub_date), MAX(pub_date)
        FROM car;
    """)
    return cur.fetchone()

@mcp.tool()
def first_15_rows():
    """Get first 15 rows."""
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM car
        ORDER BY pub_date ASC
        LIMIT 15;
    """)
    return cur.fetchall()


@mcp.tool()
def last_15_rows():
    """Get last 15 rows."""
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM car
        ORDER BY pub_date DESC
        LIMIT 15;
    """)
    return cur.fetchall()

@mcp.tool()
def order_ascending():
    """Order data ascending."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM car ORDER BY pub_date ASC;")
    return cur.fetchall()

@mcp.tool()
def order_descending():
    """Order data descending."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM car ORDER BY pub_date DESC;")
    return cur.fetchall()


@mcp.tool()
def count_car_brands():
    """Count how many unique car brands exist in the database."""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT car_make)
        FROM car;
    """)

    result = cur.fetchone()[0]
    return {"unique_car_brands": result}

def main():

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()