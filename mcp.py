from mcp.server.fastmcp import FastMCP
import psycopg2
import os
from dotenv import load_dotenv
from typing import Optional
import uvicorn
from starlette.middleware.cors import CORSMiddleware

load_dotenv()

mcp = FastMCP(
    "Cars_DB",
    stateless_http=True,
    json_response=True,
)

conn = psycopg2.connect(
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host="localhost",
    port=5432,
    database="cars_db",
)
conn.autocommit = True

VALID_COLUMNS = {
    "listing_id", "title", "price", "condition", "car_make", "model", "trim",
    "body_type", "transmission", "year", "kilometers", "engine_size_cc",
    "exterior_color", "car_customs", "car_license", "body_condition",
    "regional_specs", "fuel", "neighborhood", "city", "pub_date",
    "image_urls", "fetch_date", "modified_date", "url",
}

MAX_ROWS = 100
MAX_JOIN_ROWS = 100

UNPROTECTED_PATHS = {"/docs", "/redoc", "/openapi.json"}


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def get_cursor():
    try:
        conn.rollback()
    except Exception:
        pass
    return conn.cursor()


def validate_column(col: str) -> str:
    if col not in VALID_COLUMNS:
        raise ValueError(f"Invalid column: '{col}'. Must be one of: {VALID_COLUMNS}")
    return col


# ─── MIDDLEWARE ───────────────────────────────────────────────────────────────

class StaticTokenMiddleware:
    """Pure ASGI middleware — SSE-safe, no response buffering.

    Accepted formats:
        Authorization: Bearer <token>
        X-API-Key: <token>

    Paths in UNPROTECTED_PATHS are always allowed through.
    If token is empty string, middleware is a no-op.
    """

    def __init__(self, app, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and self.token:
            path = scope.get("path", "")

            if path not in UNPROTECTED_PATHS:
                headers = dict(scope.get("headers", []))
                auth = headers.get(b"authorization", b"").decode()
                api_key = headers.get(b"x-api-key", b"").decode().strip()

                token_valid = (
                    (auth.lower().startswith("bearer ") and auth[7:].strip() == self.token)
                    or api_key == self.token
                )

                if not token_valid:
                    body = b'{"detail": "Unauthorized. Provide Authorization: Bearer <token> or X-API-Key: <token>."}'
                    await send({
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                            (b"www-authenticate", b'Bearer error="invalid_token"'),
                        ],
                    })
                    await send({
                        "type": "http.response.body",
                        "body": body,
                        "more_body": False,
                    })
                    return

        await self.app(scope, receive, send)


# ─── 1. LIST ROWS ─────────────────────────────────────────────────────────────

@mcp.tool(name="list_rows", description="List rows from the car table")
def list_rows(
    columns: Optional[list[str]] = None,
    order_by: Optional[str] = None,
    order_dir: str = "ASC",
    limit: int = 15,
):
    limit = min(max(1, limit), MAX_ROWS)

    if order_dir.upper() not in ("ASC", "DESC"):
        raise ValueError("order_dir must be 'ASC' or 'DESC'")

    col_clause = ", ".join([validate_column(c) for c in columns]) if columns else "*"
    order_clause = f"ORDER BY {validate_column(order_by)} {order_dir.upper()}" if order_by else ""

    cur = get_cursor()
    cur.execute(f"SELECT {col_clause} FROM car {order_clause} LIMIT {limit};")
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]

    return {"columns": col_names, "rows": rows, "returned": len(rows)}


# ─── 2. COUNT RECORDS ─────────────────────────────────────────────────────────

@mcp.tool(name="count_records", description="Count records in the car table")
def count_records(
    filter_field: Optional[str] = None,
    filter_value: Optional[str] = None,
) -> dict:
    cur = get_cursor()

    if filter_field and filter_value:
        validate_column(filter_field)
        cur.execute(f"SELECT COUNT(*) FROM car WHERE {filter_field} = %s;", (filter_value,))
    else:
        cur.execute("SELECT COUNT(*) FROM car;")

    count = cur.fetchone()[0]
    return {
        "count": count,
        "filter": f"{filter_field} = {filter_value}" if filter_field else "none",
    }


# ─── 3. TABLE DESCRIPTION ─────────────────────────────────────────────────────

@mcp.tool(name="Table_Description", description="Full description of the car table")
def describe_table():
    cur = conn.cursor()
    result = {}

    cur.execute("SELECT COUNT(*) FROM car;")
    result["total_rows"] = cur.fetchone()[0]

    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'car'
        ORDER BY ordinal_position;
    """)
    cols = cur.fetchall()
    result["fields"] = [{"name": c[0], "type": c[1]} for c in cols]
    result["num_fields"] = len(cols)

    cur.execute("SELECT COUNT(DISTINCT car_make) FROM car;")
    result["unique_brands"] = cur.fetchone()[0]

    cur.execute("""
        SELECT car_make, COUNT(DISTINCT model) AS model_count
        FROM car GROUP BY car_make ORDER BY model_count DESC;
    """)
    result["models_per_brand"] = [
        {"brand": r[0], "model_count": r[1]} for r in cur.fetchall()
    ]

    cur.execute("""
        SELECT car_make, model, COUNT(DISTINCT trim) AS trim_count
        FROM car GROUP BY car_make, model ORDER BY car_make, model;
    """)
    result["trims_per_model"] = [
        {"brand": r[0], "model": r[1], "trim_count": r[2]} for r in cur.fetchall()
    ]

    cur.execute("SELECT MIN(pub_date), MAX(pub_date) FROM car;")
    first, last = cur.fetchone()
    result["pub_date_range"] = {"first": str(first), "last": str(last)}

    return result


# ─── 4. PUBLISH DATE RANGE ────────────────────────────────────────────────────

@mcp.tool(name="Get_Publish_date", description="Get the earliest and latest publish dates in the database.")
def get_pub_date_range():
    cur = conn.cursor()
    cur.execute("SELECT MIN(pub_date), MAX(pub_date) FROM car;")
    first, last = cur.fetchone()
    return {"first_pub_date": str(first), "last_pub_date": str(last)}


# ─── 5. GROUP BY ──────────────────────────────────────────────────────────────

@mcp.tool(name="Group_By", description="Group records by a field and return counts.")
def group_by(
    group_field: str,
    count_label: str = "count",
    order_dir: str = "DESC",
    limit: int = 50,
):
    validate_column(group_field)
    limit = min(max(1, limit), MAX_ROWS)

    if order_dir.upper() not in ("ASC", "DESC"):
        raise ValueError("order_dir must be 'ASC' or 'DESC'")

    cur = conn.cursor()
    cur.execute(f"""
        SELECT {group_field}, COUNT(*) AS {count_label}
        FROM car GROUP BY {group_field}
        ORDER BY COUNT(*) {order_dir.upper()}
        LIMIT {limit};
    """)
    rows = cur.fetchall()
    return {
        "group_by": group_field,
        "results": [{"value": r[0], count_label: r[1]} for r in rows],
    }


# ─── 6. JOIN QUERY ────────────────────────────────────────────────────────────

@mcp.tool(name="query_with_join", description="Run a JOIN query between 'car' and another table.")
def query_with_join(
    join_table: str,
    join_on: str,
    select_columns: Optional[list[str]] = None,
    where_clause: Optional[str] = None,
    limit: int = 100,
):
    limit = min(max(1, limit), MAX_JOIN_ROWS)
    col_clause = ", ".join(select_columns) if select_columns else f"car.*, {join_table}.*"
    query = f"""
        SELECT {col_clause}
        FROM car JOIN {join_table} ON {join_on}
        {"WHERE " + where_clause if where_clause else ""}
        LIMIT {limit};
    """
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]
    return {"columns": col_names, "rows": rows, "returned": len(rows)}


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    static_api_token = os.getenv("STATIC_API_TOKEN", "").strip()
    if not static_api_token:
        print("WARNING: STATIC_API_TOKEN is not set — all requests will be allowed!", flush=True)
    else:
        print(f"INFO: Static token loaded ({len(static_api_token)} chars)", flush=True)

    app = mcp.sse_app()

    # CORS is registered first (innermost layer)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )

    # Token auth wraps everything — pure ASGI class, NOT BaseHTTPMiddleware
    # SSE-safe: never buffers the response body, just passes scope through
    app = StaticTokenMiddleware(app, token=static_api_token)

    uvicorn.run(app, host="0.0.0.0", port=8080, http="h11", log_level="info")


if __name__ == "__main__":
    main()