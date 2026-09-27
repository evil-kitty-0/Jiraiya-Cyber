import urllib.request
import json

url = "http://127.0.0.1:8080/v1/chat/completions"

data = {
    "messages": [
        {
            "role": "user",
            "content": "Hello Jiraiya, reply in one short sentence."
        }
    ],
    "temperature": 0.7,
    "max_tokens": 100
}

req = urllib.request.Request(
    url,
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

with urllib.request.urlopen(req, timeout=120) as response:
    result = json.loads(response.read().decode("utf-8"))

print(result["choices"][0]["message"]["content"])
