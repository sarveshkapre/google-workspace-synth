from __future__ import annotations

from typing import Any


def ensure_license(
    service: Any,
    *,
    product_id: str,
    sku_id: str,
    user_email: str,
    dry_run: bool,
) -> bool:
    if has_license(service, product_id=product_id, sku_id=sku_id, user_email=user_email):
        return False
    if dry_run:
        return True
    body = {"userId": user_email}
    service.licenseAssignments().insert(productId=product_id, skuId=sku_id, body=body).execute()
    return True


def has_license(service: Any, *, product_id: str, sku_id: str, user_email: str) -> bool:
    try:
        service.licenseAssignments().get(
            productId=product_id, skuId=sku_id, userId=user_email
        ).execute()
        return True
    except Exception as exc:
        if _is_http_error(exc, 404):
            return False
        raise


def _is_http_error(exc: Exception, status: int) -> bool:
    resp = getattr(exc, "resp", None)
    code = getattr(resp, "status", None)
    return code == status
