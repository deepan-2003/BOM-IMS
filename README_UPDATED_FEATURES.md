# Bharathi Oil Mill – Updated Streamlit Project

## Added
- Chilli combo quick packages: 250 g ₹50, 500 g ₹100, 750 g ₹150, 1 kg ₹200.
- Saved-bill panel with PDF download and print-ready HTML download; it remains visible across Streamlit reruns in the current browser session.
- A4 PDF bill generation.
- Professional Excel report export with Bills, Transactions, Expenses, Stock Movements and Daily Summary sheets.

## Run
1. Install dependencies: `pip install -r requirements.txt`
2. Configure PostgreSQL using `.streamlit/secrets.toml` or `DATABASE_URL`.
3. Run: `streamlit run Home.py`

Existing database schema is retained. The combo rows use the existing `bill_items` table with a nullable `service_id`.


## Labour and expense updates
- Labourers can be deactivated from Labour Management → Worker Roster → Delete Labourer. This is a soft delete, so attendance and wage history remain available.
- The Reports → Expenses view and Excel export combine manual expenses with attendance wages/advances and machine maintenance costs. These are read from their original tables; no duplicate expense rows are inserted.
- Manually entered expense rows with Labour, Maintenance, or Machine Maintenance categories are excluded from the combined expense view and the separate Other Expenses total to prevent double counting.
- Excel export now includes separate Labour Costs and Machine Maintenance sheets in addition to the combined Expenses sheet.
