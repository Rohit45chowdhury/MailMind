from google_auth_oauthlib.flow import InstalledAppFlow
from calendar_service import SCOPES, TOKEN_FILE

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)  # opens browser for consent

with open(TOKEN_FILE, "w") as f:
    f.write(creds.to_json())
print("token.json saved")