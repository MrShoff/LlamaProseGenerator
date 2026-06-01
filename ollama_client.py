from __future__ import annotations

import httpx

_DEFAULT_TIMEOUT = 600  # 10 minutes — sufficient for 3,800-word scene generation


def generate(
    base_url: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    num_ctx: int = 8192,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
        },
        "stream": False,
    }
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
    except httpx.ConnectError:
        raise ConnectionError(
            f"Cannot reach Ollama at {base_url}. Is it running?"
        )
    except httpx.TimeoutException:
        raise TimeoutError(
            f"Generation timed out after {timeout}s. "
            "Try increasing the timeout or reducing num_ctx."
        )
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Ollama returned HTTP {exc.response.status_code}: "
            f"{exc.response.text[:300]}"
        )

    data = response.json()
    try:
        return data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected Ollama response shape: {data!r}"
        ) from exc


def check_connectivity(base_url: str, timeout: int = 5) -> tuple[bool, str]:
    """Returns (is_connected, error_message). Error message is empty on success."""
    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}/api/tags", timeout=timeout
        )
        if response.status_code == 200:
            return True, ""
        return False, f"HTTP {response.status_code}"
    except httpx.ConnectError:
        return False, "Connection refused — is Ollama running?"
    except httpx.TimeoutException:
        return False, f"Connection timed out after {timeout}s"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def list_local_models(base_url: str, timeout: int = 5) -> list[str]:
    """Returns model names available in the local Ollama instance."""
    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}/api/tags", timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:  # noqa: BLE001
        return []
