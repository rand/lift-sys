from __future__ import annotations

from lift_sys.auth.token_store import TokenStore


def test_token_round_trip() -> None:
    storage: dict[str, str] = {}
    key = TokenStore.generate_key()
    store = TokenStore(storage, key)

    payload = {"access_token": "abc", "refresh_token": "def"}
    store.save_tokens("user", "openai", payload)

    assert storage  # encrypted payload stored
    loaded = store.load_tokens("user", "openai")
    assert loaded == payload

    store.delete_tokens("user", "openai")
    assert store.load_tokens("user", "openai") is None
