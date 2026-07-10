import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

DB_PATH = Path(__file__).resolve().parents[1] / 'data' / 'sales_support.db'
LOGGER = logging.getLogger('data-insights-app')

DANGEROUS_SQL = re.compile(
    r'\b(DELETE|DROP|TRUNCATE|ALTER|UPDATE|INSERT|REPLACE|CREATE|ATTACH|DETACH|VACUUM|PRAGMA)\b',
    re.IGNORECASE,
)

ALLOWED_TABLES = {'customers', 'deals', 'support_tickets'}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_if_missing() -> None:
    if DB_PATH.exists():
        return
    import subprocess, sys
    script = DB_PATH.with_name('generate_data.py')
    LOGGER.info('Database missing. Generating sample data with %s', script)
    subprocess.check_call([sys.executable, str(script)])


def validate_sql(sql: str) -> str:
    sql_clean = sql.strip().rstrip(';')
    if not sql_clean.lower().startswith('select'):
        raise ValueError('Only SELECT queries are allowed.')
    if DANGEROUS_SQL.search(sql_clean):
        raise ValueError('Blocked potentially dangerous SQL operation.')
    if ';' in sql_clean:
        raise ValueError('Only one SQL statement is allowed.')
    return sql_clean


def run_safe_query(sql: str, limit: int = 50) -> list[dict[str, Any]]:
    sql_clean = validate_sql(sql)
    limited_sql = f'SELECT * FROM ({sql_clean}) LIMIT ?'
    LOGGER.info('Running safe SQL query: %s | limit=%s', sql_clean, limit)
    with get_connection() as conn:
        rows = conn.execute(limited_sql, (limit,)).fetchall()
    return [dict(row) for row in rows]


def table_schema() -> dict[str, list[str]]:
    with get_connection() as conn:
        schema = {}
        for table in ALLOWED_TABLES:
            rows = conn.execute(f'PRAGMA table_info({table})').fetchall()
            schema[table] = [f"{r['name']} {r['type']}" for r in rows]
    return schema


def kpis() -> dict[str, Any]:
    with get_connection() as conn:
        customers = conn.execute('SELECT COUNT(*) AS n FROM customers').fetchone()['n']
        deals = conn.execute('SELECT COUNT(*) AS n FROM deals').fetchone()['n']
        tickets = conn.execute('SELECT COUNT(*) AS n FROM support_tickets').fetchone()['n']
        revenue = conn.execute("SELECT COALESCE(SUM(deal_value), 0) AS v FROM deals WHERE status='won'").fetchone()['v']
        open_deals = conn.execute("SELECT COUNT(*) AS n FROM deals WHERE status='open'").fetchone()['n']
    return {
        'customers': customers,
        'deals': deals,
        'support_tickets': tickets,
        'won_revenue': round(revenue, 2),
        'open_deals': open_deals,
    }


def revenue_by_region() -> pd.DataFrame:
    sql = '''
    SELECT c.region, ROUND(SUM(d.deal_value), 2) AS won_revenue
    FROM deals d JOIN customers c ON c.customer_id = d.customer_id
    WHERE d.status='won'
    GROUP BY c.region
    ORDER BY won_revenue DESC
    '''
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn)


def sample_rows(table: str, n: int = 5) -> pd.DataFrame:
    if table not in ALLOWED_TABLES:
        raise ValueError('Unknown table')
    with get_connection() as conn:
        return pd.read_sql_query(f'SELECT * FROM {table} LIMIT ?', conn, params=(n,))
