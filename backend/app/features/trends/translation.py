"""DeepL text translation (one bounded batch, transient retries, no persistence).

API: https://developers.deepl.com/api-reference/translate
Free-plan keys end with ":fx" and use api-free.deepl.com; others use api.deepl.com.
Errors never include the key, request texts or response bodies.
"""
import time

import httpx

MAX_TEXTS = 50  # DeepL limit per request
MAX_RETRIES = 2


class TranslationError(RuntimeError):
    def __init__(self, code: str, status_code: int | None = None):
        self.code = code
        self.status_code = status_code
        super().__init__(f"Translation failed: {code}")


def endpoint(api_key: str) -> str:
    host = "api-free.deepl.com" if api_key.endswith(":fx") else "api.deepl.com"
    return f"https://{host}/v2/translate"


def translate(texts: list[str], *, api_key: str, source_lang: str = "EN", target_lang: str = "KO",
              timeout: float = 20, client: httpx.Client | None = None) -> list[str]:
    """Translate up to MAX_TEXTS strings in order. Empty strings are returned unchanged."""
    if not api_key:
        raise TranslationError("missing_api_key")
    if len(texts) > MAX_TEXTS:
        raise ValueError(f"At most {MAX_TEXTS} texts per request")
    indices = [i for i, text in enumerate(texts) if text.strip()]
    if not indices:
        return list(texts)

    def fetch(active: httpx.Client) -> list[str]:
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = active.post(
                    endpoint(api_key), timeout=timeout, follow_redirects=False,
                    headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
                    json={"text": [texts[i] for i in indices], "source_lang": source_lang, "target_lang": target_lang},
                )
                response.raise_for_status()
                translated = [t["text"] for t in response.json()["translations"]]
            except httpx.TimeoutException:
                raise TranslationError("timeout") from None
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if (status == 429 or 500 <= status < 600) and attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
                code = {456: "quota_exceeded", 429: "rate_limited", 403: "invalid_api_key"}.get(status, "http_status")
                raise TranslationError(code, status) from None
            except httpx.RequestError:
                raise TranslationError("network") from None
            except (ValueError, KeyError, TypeError):
                raise TranslationError("invalid_response") from None
            break
        if len(translated) != len(indices):
            raise TranslationError("invalid_response")
        result = list(texts)
        for i, text in zip(indices, translated):
            result[i] = text
        return result

    if client is not None:
        return fetch(client)
    with httpx.Client() as active:
        return fetch(active)
