import logging
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from .config import settings

logger = logging.getLogger("skufinder.db")

UPSERT_SQL = """
insert into public.sku_stock (
    facility, sku_code, item_type_name, inventory_type, shelf,
    enabled_for_inventory_allocation, enabled_for_inventory_sync,
    enabled_for_sku_mixing, enabled_for_shelf_hold,
    quantity, quantity_blocked, quantity_not_found, excess_quantity,
    net_variance, quantity_damaged, priority, section, batch_code, expiry
) values (
    %(facility)s, %(sku_code)s, %(item_type_name)s, %(inventory_type)s, %(shelf)s,
    %(enabled_for_inventory_allocation)s, %(enabled_for_inventory_sync)s,
    %(enabled_for_sku_mixing)s, %(enabled_for_shelf_hold)s,
    %(quantity)s, %(quantity_blocked)s, %(quantity_not_found)s, %(excess_quantity)s,
    %(net_variance)s, %(quantity_damaged)s, %(priority)s, %(section)s, %(batch_code)s, %(expiry)s
)
on conflict (facility, sku_code, shelf) do update set
    item_type_name = excluded.item_type_name,
    inventory_type = excluded.inventory_type,
    enabled_for_inventory_allocation = excluded.enabled_for_inventory_allocation,
    enabled_for_inventory_sync = excluded.enabled_for_inventory_sync,
    enabled_for_sku_mixing = excluded.enabled_for_sku_mixing,
    enabled_for_shelf_hold = excluded.enabled_for_shelf_hold,
    quantity = excluded.quantity,
    quantity_blocked = excluded.quantity_blocked,
    quantity_not_found = excluded.quantity_not_found,
    excess_quantity = excluded.excess_quantity,
    net_variance = excluded.net_variance,
    quantity_damaged = excluded.quantity_damaged,
    priority = excluded.priority,
    section = excluded.section,
    batch_code = excluded.batch_code,
    expiry = excluded.expiry,
    updated_at = now();
"""


@contextmanager
def get_connection():
    conn = psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        dbname=settings.db_name,
    )
    try:
        yield conn
    finally:
        conn.close()


def upsert_rows(rows: list[dict]) -> int:
    if not rows:
        return 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, UPSERT_SQL, rows, page_size=500)
        conn.commit()
    logger.info("Upserted %d sku_stock rows", len(rows))
    return len(rows)


def search_skus(query: str | None, limit: int = 100) -> list[dict]:
    sql = """
        select facility, sku_code, item_type_name, inventory_type, shelf,
               quantity, quantity_blocked, quantity_not_found, excess_quantity,
               net_variance, quantity_damaged, priority, section, batch_code,
               expiry, updated_at
        from public.sku_stock
    """
    params: list = []
    if query:
        sql += " where sku_code ilike %s or item_type_name ilike %s"
        like = f"%{query}%"
        params.extend([like, like])
    sql += " order by updated_at desc limit %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())
