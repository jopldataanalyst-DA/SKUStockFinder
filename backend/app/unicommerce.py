import csv
import io
import logging
import re
import time

import requests

from .config import settings

logger = logging.getLogger("skufinder.unicommerce")

EXPORT_COLUMNS = [
    "facility",
    "skuCode",
    "itemTypeName",
    "inventoryType",
    "shelf",
    "enabledForInventoryAllocation",
    "enabledForInventorySync",
    "enabledForSkuMixing",
    "enabledForShelfHold",
    "quantity",
    "quantityBlocked",
    "quantityNotFound",
    "excessQuantity",
    "netVariance",
    "quantityDamaged",
    "priority",
    "section",
    "batchCode",
    "expiry",
]

# Unicommerce's CSV export uses human-readable headers, not the camelCase
# names passed in exportColums. Map them explicitly to our snake_case columns.
HEADER_MAP = {
    "facility": "facility",
    "item type sku code": "sku_code",
    "item type name": "item_type_name",
    "inventory type": "inventory_type",
    "shelf": "shelf",
    "inventory allocation": "enabled_for_inventory_allocation",
    "inventory sync": "enabled_for_inventory_sync",
    "sku mixing": "enabled_for_sku_mixing",
    "shelf on hold": "enabled_for_shelf_hold",
    "quantity": "quantity",
    "quantity blocked": "quantity_blocked",
    "quantity not found": "quantity_not_found",
    "excess quantity": "excess_quantity",
    "net variance": "net_variance",
    "quantity damaged": "quantity_damaged",
    "priority": "priority",
    "section": "section",
    "batch code": "batch_code",
    "expiry": "expiry",
}

BOOL_FIELDS = {
    "enabled_for_inventory_allocation",
    "enabled_for_inventory_sync",
    "enabled_for_sku_mixing",
    "enabled_for_shelf_hold",
}
INT_FIELDS = {
    "quantity",
    "quantity_blocked",
    "quantity_not_found",
    "excess_quantity",
    "net_variance",
    "quantity_damaged",
}

_CAMEL_RE = re.compile(r"(?<!^)(?=[A-Z])")


def _camel_to_snake(name: str) -> str:
    return _CAMEL_RE.sub("_", name).lower()


class _TokenManager:
    """Fetches and auto-refreshes the Unicommerce OAuth bearer token."""

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0.0

    def _fetch_with_password(self) -> dict:
        resp = requests.get(
            f"{settings.unicommerce_base_url}/oauth/token",
            params={
                "grant_type": "password",
                "client_id": settings.unicommerce_client_id,
                "username": settings.unicommerce_username,
                "password": settings.unicommerce_password,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def _fetch_with_refresh(self) -> dict:
        resp = requests.get(
            f"{settings.unicommerce_base_url}/oauth/token",
            params={
                "grant_type": "refresh_token",
                "client_id": settings.unicommerce_client_id,
                "refresh_token": self._refresh_token,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def get_token(self) -> str:
        now = time.monotonic()
        if self._access_token and now < self._expires_at:
            return self._access_token

        data = None
        if self._refresh_token:
            try:
                data = self._fetch_with_refresh()
            except requests.HTTPError:
                logger.warning("Refresh token rejected, falling back to password grant")
                data = None
        if data is None:
            data = self._fetch_with_password()

        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        # refresh a little early to avoid racing against expiry
        self._expires_at = now + int(data.get("expires_in", 3600)) - 60
        return self._access_token


_token_manager = _TokenManager()


def _headers(facility: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"bearer {_token_manager.get_token()}",
        "Facility": facility,
    }


def create_export_job(facility: str) -> str:
    resp = requests.post(
        f"{settings.unicommerce_base_url}/services/rest/v1/export/job/create",
        headers=_headers(facility),
        json={
            "exportJobTypeName": "Shelfwise Inventory",
            "exportColums": EXPORT_COLUMNS,
            "frequency": "ONETIME",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    job_code = data.get("jobCode") or data.get("job_code")
    if not job_code:
        raise RuntimeError(f"No jobCode in create response: {data}")
    return job_code


def _poll_job_status(facility: str, job_code: str, timeout_s: int = 300, interval_s: int = 5) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        resp = requests.post(
            f"{settings.unicommerce_base_url}/services/rest/v1/export/job/status",
            headers=_headers(facility),
            json={"jobCode": job_code},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = (data.get("status") or "").upper()
        if status in ("SUCCESSFUL", "COMPLETE", "COMPLETED", "SUCCESS"):
            return data
        if status in ("FAILED", "ERROR"):
            raise RuntimeError(f"Export job {job_code} failed: {data}")
        time.sleep(interval_s)
    raise TimeoutError(f"Export job {job_code} did not complete within {timeout_s}s")


def _download_csv(facility: str, file_path: str) -> str:
    url = file_path if file_path.startswith("http") else f"{settings.unicommerce_base_url}{file_path}"
    resp = requests.get(url, headers=_headers(facility), timeout=60)
    resp.raise_for_status()
    return resp.text


ALL_ROW_FIELDS = set(HEADER_MAP.values())


def _parse_csv(facility: str, csv_text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = []
    for raw in reader:
        row: dict = {f: None for f in ALL_ROW_FIELDS}
        for header, value in raw.items():
            field = HEADER_MAP.get(header.strip().lower())
            if not field:
                continue
            row[field] = value.strip() if isinstance(value, str) else value

        # the CSV's facility column is a display name; keep the facility code
        # we requested with, since that's what the unique key is built on
        row["facility"] = facility
        row["shelf"] = row.get("shelf") or ""

        for f in INT_FIELDS:
            val = row.get(f)
            try:
                row[f] = int(val) if val not in (None, "") else 0
            except ValueError:
                row[f] = 0
        for f in BOOL_FIELDS:
            val = row.get(f)
            row[f] = str(val).strip().lower() in ("true", "1", "yes") if val not in (None, "") else None
        row["expiry"] = row.get("expiry") or None
        rows.append(row)
    return rows


def fetch_facility_inventory(facility: str) -> list[dict]:
    logger.info("Creating export job for facility %s", facility)
    job_code = create_export_job(facility)
    status_data = _poll_job_status(facility, job_code)
    file_path = status_data.get("filePath")
    if not file_path:
        raise RuntimeError(f"No filePath in completed status response: {status_data}")
    csv_text = _download_csv(facility, file_path)
    rows = _parse_csv(facility, csv_text)
    logger.info("Fetched %d rows for facility %s", len(rows), facility)
    return rows


def fetch_all_facilities() -> list[dict]:
    all_rows: list[dict] = []
    for facility in settings.facilities:
        try:
            all_rows.extend(fetch_facility_inventory(facility))
        except Exception:
            logger.exception("Failed fetching inventory for facility %s", facility)
    return all_rows
