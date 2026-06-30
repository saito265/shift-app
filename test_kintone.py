import requests
from dotenv import load_dotenv
import os

load_dotenv()

res = requests.get(
    f"https://{os.getenv('KINTONE_DOMAIN')}/k/v1/records.json",
    headers={"X-Cybozu-API-Token": os.getenv("API_TOKEN_STAFF")},
    params={"app": os.getenv("APP_ID_STAFF")}
)

print("ステータスコード:", res.status_code)
print("レスポンス:", res.json())
