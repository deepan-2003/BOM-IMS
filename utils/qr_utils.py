"""QR Code generation utilities for Bharathi Oil Mill bills."""

import qrcode
import json
import io
import base64
from datetime import datetime


def generate_bill_qr(bill_data: dict) -> str:
    """
    Generate a QR code for a bill and return as base64 PNG string.
    
    The QR encodes a compact JSON payload:
      bill_number, date, customer, total, items (name + qty + amount)
    """
    payload = {
        "app": "BharathaOilMill",
        "bill": bill_data.get("bill_number", ""),
        "date": bill_data.get("created_at", datetime.now()).strftime("%d-%m-%Y %H:%M") 
                if hasattr(bill_data.get("created_at", ""), "strftime") 
                else str(bill_data.get("created_at", "")),
        "customer": bill_data.get("customer_name") or "Walk-in",
        "phone": bill_data.get("customer_phone") or "",
        "total": float(bill_data.get("total", 0)),
        "payment": bill_data.get("payment_method") or "cash",
        "status": bill_data.get("payment_status") or "paid",
    }
    if bill_data.get("items"):
        payload["items"] = [
            {
                "s": item.get("service_name", ""),
                "q": float(item.get("quantity_kg", 0)),
                "a": float(item.get("amount", 0)),
            }
            for item in bill_data["items"]
        ]

    qr_text = json.dumps(payload, separators=(",", ":"))

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(qr_text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1a1a2e", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def qr_to_html_img(b64_string: str, size: int = 150) -> str:
    """Return an <img> tag with embedded base64 QR PNG."""
    return f'<img src="data:image/png;base64,{b64_string}" width="{size}" height="{size}" />'
