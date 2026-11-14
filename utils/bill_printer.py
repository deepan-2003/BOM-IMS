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


def generate_bill_pdf(bill: dict, items: list, oil_processing: list = None) -> bytes:
    """Create a clean A4 PDF bill; returned as bytes for Streamlit download."""
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import mm

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
                            topMargin=14*mm, bottomMargin=14*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="MillTitle", parent=styles["Title"], fontSize=20,
                              textColor=colors.HexColor("#17324d"), alignment=TA_CENTER,
                              spaceAfter=3))
    styles.add(ParagraphStyle(name="Subtle", parent=styles["Normal"], fontSize=8,
                              textColor=colors.HexColor("#64748b"), alignment=TA_CENTER))
    story = [Paragraph("BHARATHI OIL MILL", styles["MillTitle"]),
             Paragraph("Traditional Milling • Spice Grinding • Cold-Press Oil", styles["Subtle"]),
             Spacer(1, 8*mm)]
    created = bill.get("created_at")
    date_text = created.strftime("%d-%m-%Y %I:%M %p") if hasattr(created, "strftime") else str(created or "")
    meta = [
        ["Bill Number", str(bill.get("bill_number", "")), "Date", date_text],
        ["Customer", str(bill.get("customer_name") or "Walk-in"), "Phone", str(bill.get("customer_phone") or "—")],
        ["Payment", str(bill.get("payment_method") or "—").upper(), "Status", str(bill.get("payment_status") or "—").upper()],
    ]
    t = Table(meta, colWidths=[25*mm, 62*mm, 20*mm, 62*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR",(0,0),(0,-1),colors.HexColor("#334155")),
        ("TEXTCOLOR",(2,0),(2,-1),colors.HexColor("#334155")),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
        ("FONTSIZE",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#dbe3ec")),
        ("PADDING",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"MIDDLE")
    ]))
    story += [t, Spacer(1, 7*mm)]
    data = [["Description", "Quantity", "Rate (₹)", "Amount (₹)"]]
    for item in items:
        q = float(item.get("quantity_kg") or 0)
        data.append([str(item.get("service_name") or "Service"),
                     f"{q:g} kg", f"{float(item.get('rate_per_kg') or 0):,.2f}",
                     f"{float(item.get('amount') or 0):,.2f}"])
    for op in oil_processing or []:
        data.append([f"{op.get('seed_type','Oil')} processing / cake buy-back",
                     f"{float(op.get('input_kg') or 0):g} kg",
                     "—", f"{abs(float(op.get('net_amount') or 0)):,.2f}"])
    table = Table(data, colWidths=[83*mm, 30*mm, 27*mm, 29*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#17324d")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#dbe3ec")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),
        ("ALIGN",(1,1),(-1,-1),"RIGHT"),("PADDING",(0,0),(-1,-1),7),
    ]))
    story += [table, Spacer(1, 6*mm)]
    subtotal = float(bill.get("subtotal") or 0)
    discount = float(bill.get("discount") or 0)
    total = float(bill.get("total") or 0)
    totals = [["Subtotal", f"₹{subtotal:,.2f}"], ["Discount", f"− ₹{discount:,.2f}"],
              ["TOTAL", f"₹{total:,.2f}"]]
    tt = Table(totals, colWidths=[130*mm,39*mm], hAlign="RIGHT")
    tt.setStyle(TableStyle([
        ("ALIGN",(1,0),(1,-1),"RIGHT"),("FONTNAME",(0,0),(-1,-1),"Helvetica"),
        ("FONTSIZE",(0,0),(-1,-1),9),("PADDING",(0,0),(-1,-1),6),
        ("LINEABOVE",(0,2),(-1,2),1,colors.HexColor("#17324d")),
        ("BACKGROUND",(0,2),(-1,2),colors.HexColor("#eaf1f7")),
        ("FONTNAME",(0,2),(-1,2),"Helvetica-Bold"),("FONTSIZE",(0,2),(-1,2),12),
    ]))
    story += [tt, Spacer(1, 12*mm),
              Paragraph("Thank you for choosing Bharathi Oil Mill!", styles["Subtle"])]
    if bill.get("notes"):
        story += [Spacer(1,3*mm), Paragraph(f"Notes: {bill['notes']}", styles["Normal"])]
    doc.build(story)
    return buffer.getvalue()
