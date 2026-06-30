import requests, os
from dotenv import load_dotenv
load_dotenv()

res = requests.get(
    f"https://{os.getenv('KINTONE_DOMAIN')}/k/v1/records.json",
    headers={"X-Cybozu-API-Token": os.getenv("API_TOKEN_STAFF")},
    params={"app": os.getenv("APP_ID_STAFF")}
)
print(res.status_code)
print(res.json())
