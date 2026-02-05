import requests

API_KEY = "JN82rm9FmXsc50yp2PXc1rCEHVzDGkb9aCsKBdxCBu5VKIMuhLDwI557Wuik"

def send_sms(phone, message):
    print("SMS FUNCTION CALLED →", phone, message)
    url = "https://www.fast2sms.com/dev/bulkV2"

    payload = {
        "authorization": API_KEY,
        "route": "d",
        "message": message,
        "language": "english",
        "numbers": phone
    }

    response = requests.get(url, params=payload)

    return response.json()
