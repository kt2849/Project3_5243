
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

def save_to_google_sheets(df, sheet_name="Responses"):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Load credentials from Streamlit secrets
    creds_dict = json.loads(st.secrets["GSPREAD_KEY"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    client = gspread.authorize(creds)
    sheet = client.open("Trivia_Responses").worksheet(sheet_name)

    # Append each row
    for _, row in df.iterrows():
        sheet.append_row(row.astype(str).tolist())
