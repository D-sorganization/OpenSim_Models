import requests

url = "https://api.github.com/orgs/D-sorganization/actions/runners"
headers = {"Accept": "application/vnd.github.v3+json"}

try:
    response = requests.get(url, headers=headers)
    print(response.status_code)
    print(response.text[:200])
except Exception as e:
    print(e)
