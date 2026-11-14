"""
Bill HTML generation for Bharathi Oil Mill.
Produces a styled, printable HTML string with an embedded QR code.
"""

from datetime import datetime
from utils.qr_utils import generate_bill_qr


MILL_INFO = {
    "name": "Bharathi Oil Mill",
    "tagline": "Traditional Cold-Press & Mill Services",
    "address": "Your Address, City - 000000",
    "phone": "+91 XXXXX XXXXX",
    "gstin": "",
}


def generate_bill_html(bill: dict, items: list, oil_processing: list = None) -> str:
    qr_b64 = generate_bill_qr({**bill, "items": items})

    rows = ""
    for item in items:
        rows += f"""
        <tr>
            <td>{item['service_name']}</td>
            <td style="text-align:center">{item['quantity_kg']:.3f} kg</td>
            <td style="text-align:right">₹{item['rate_per_kg']:.2f}</td>
            <td style="text-align:right">₹{item['amount']:.2f}</td>
        </tr>"""

    oil_rows = ""
    if oil_processing:
        for op in oil_processing:
            direction = "← You Pay" if op['net_amount'] > 0 else "→ We Pay"
            oil_rows += f"""
            <tr style="background:#fffbea">
                <td colspan="2">{op['seed_type']} Oil — {op['input_kg']:.3f} kg
                    <br><small>Processing fee: ₹{op['processing_fee']:.2f} | 
                    Oil cake {op['oil_cake_kg']:.3f} kg @ ₹{op['oil_cake_rate']:.2f} = ₹{op['oil_cake_value']:.2f}</small>
                </td>
                <td style="text-align:center">{direction}</td>
                <td style="text-align:right">₹{abs(op['net_amount']):.2f}</td>
            </tr>"""

    created = bill.get('created_at', datetime.now())
    if hasattr(created, 'strftime'):
        date_str = created.strftime("%d %b %Y, %I:%M %p")
    else:
        date_str = str(created)

    reminder_row = ""
    if bill.get('reminder_date'):
        reminder_row = f"""
        <tr style="color:#e74c3c">
            <td colspan="4"><strong>⏰ Payment Due By:</strong> {bill['reminder_date']}</td>
        </tr>"""

    status_color = "#27ae60" if bill.get('payment_status') == 'paid' else "#e74c3c"
    status_text = (bill.get('payment_status') or 'paid').upper()

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size:13px; color:#222; background:#fff; padding:16px; }}
  .header {{ display:flex; justify-content:space-between; align-items:flex-start; border-bottom:2px solid #c0392b; padding-bottom:10px; margin-bottom:12px; }}
  .mill-name {{ font-size:22px; font-weight:700; color:#c0392b; }}
  .tagline {{ font-size:11px; color:#666; margin-top:2px; }}
  .bill-meta {{ text-align:right; font-size:12px; }}
  .bill-no {{ font-size:16px; font-weight:700; color:#2c3e50; }}
  .status-badge {{ display:inline-block; padding:2px 10px; border-radius:12px; font-size:11px; font-weight:700; color:#fff; background:{status_color}; }}
  table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
  th {{ background:#2c3e50; color:#fff; padding:7px 8px; text-align:left; font-size:12px; }}
  td {{ padding:6px 8px; border-bottom:1px solid #eee; }}
  .totals {{ margin-top:12px; text-align:right; }}
  .totals table {{ width:auto; float:right; }}
  .totals td {{ border:none; padding:3px 6px; }}
  .grand-total {{ font-size:16px; font-weight:700; color:#c0392b; }}
  .footer {{ clear:both; margin-top:16px; border-top:1px dashed #ccc; padding-top:8px; font-size:11px; color:#888; text-align:center; }}
  .qr-section {{ text-align:center; margin-top:10px; }}
  .qr-section img {{ border:1px solid #ddd; border-radius:4px; padding:4px; }}
  .customer-box {{ background:#f8f9fa; border-radius:6px; padding:8px 12px; margin-bottom:10px; font-size:12px; }}
  @media print {{
    body {{ padding:0; }}
    .no-print {{ display:none; }}
  }}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="mill-name">🏭 {MILL_INFO['name']}</div>
    <div class="tagline">{MILL_INFO['tagline']}</div>
    <div style="font-size:11px;color:#555;margin-top:4px">{MILL_INFO['address']}<br>📞 {MILL_INFO['phone']}</div>
  </div>
  <div class="bill-meta">
    <div class="bill-no">#{bill.get('bill_number','')}</div>
    <div style="margin-top:4px">{date_str}</div>
    <div style="margin-top:4px"><span class="status-badge">{status_text}</span></div>
    <div style="margin-top:4px;font-size:11px">{(bill.get('payment_method') or 'cash').upper()}</div>
  </div>
</div>

<div class="customer-box">
  👤 <strong>{bill.get('customer_name') or 'Walk-in Customer'}</strong>
  {'&nbsp;&nbsp;📞 ' + bill['customer_phone'] if bill.get('customer_phone') else ''}
  {'<br>📝 ' + bill['notes'] if bill.get('notes') else ''}
</div>

<table>
  <thead>
    <tr>
      <th>Service / Item</th>
      <th style="text-align:center">Quantity</th>
      <th style="text-align:right">Rate/kg</th>
      <th style="text-align:right">Amount</th>
    </tr>
  </thead>
  <tbody>
    {rows}
    {oil_rows}
    {reminder_row}
  </tbody>
</table>

<div class="totals">
  <table>
    <tr><td>Subtotal:</td><td><strong>₹{bill.get('subtotal',0):.2f}</strong></td></tr>
    {"<tr><td>Discount:</td><td style='color:#e74c3c'>-₹" + f"{bill.get('discount',0):.2f}</td></tr>" if bill.get('discount',0) > 0 else ""}
    <tr><td class="grand-total">TOTAL:</td><td class="grand-total">₹{bill.get('total',0):.2f}</td></tr>
  </table>
</div>

<div class="qr-section">
  <div style="font-size:11px;color:#888;margin-bottom:4px">Scan to verify bill</div>
  <img src="data:image/png;base64,{qr_b64}" width="130" height="130" />
</div>

<div class="footer">
  Thank you for choosing Bharathi Oil Mill! &nbsp;|&nbsp; This is a computer-generated bill.
</div>
</body>
</html>"""
    return html
