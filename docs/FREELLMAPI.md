# FreeLLMAPI backend

Jiraiya-Cyber can use FreeLLMAPI as its inference backend. This keeps the
actual model inference off the device: FreeLLMAPI routes requests to the
free-tier providers whose keys you configure.

## Setup

1. Install and run FreeLLMAPI separately:
   https://github.com/tashfeenahmed/freellmapi
2. Add your provider keys in its dashboard.
3. Copy the unified API key from the FreeLLMAPI Keys page.
4. Configure Jiraiya before starting it:

```bash
export JIRAIYA_FREELLMAPI_URL="http://127.0.0.1:3001/v1"
export JIRAIYA_FREELLMAPI_KEY="freellmapi-your-unified-key"
export JIRAIYA_FREELLMAPI_MODEL="auto"
```

For a remote FreeLLMAPI host, replace the URL with that host's `/v1`
endpoint.

When the key is configured, Jiraiya:

- uses FreeLLMAPI first for normal, coding, cyber, and web-answer inference;
- does not start the local llama.cpp model for normal operation;
- lets FreeLLMAPI choose the model/provider and fail over on provider limits;
- falls back to the existing local GGUF model if the FreeLLMAPI gateway is
  temporarily unavailable.

The reported 7.4 billion tokens/month is the aggregate listed free-tier
capacity across the provider fleet, not a single guaranteed quota. Each
provider still has its own limits and requires its own key where applicable.
