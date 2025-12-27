from __future__ import annotations

import base64
import secrets
import string
from typing import Iterable

MASK_TOKEN_KEYS = {"m", "~m"}
DEFAULT_SECRET_LENGTH = 32


def generate_secret(length: int = DEFAULT_SECRET_LENGTH) -> str:
    """
    Generate a pseudo-random secret for masking operations.
    Uses URL-safe characters so it can be safely written to config.toml.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def encode_mask(secret: str, clear: str) -> str:
    """
    Encode a clear-text string using the provided secret.
    The algorithm mirrors the sample provided by the user: a simple
    Vigenère-style shift followed by urlsafe base64 encoding.
    """
    if clear is None:
        return ""
    secret = (secret or "").strip()
    if not secret:
        return clear

    encoded_chars: list[str] = []
    secret_len = len(secret)
    for idx, ch in enumerate(clear):
        key_ch = secret[idx % secret_len]
        encoded_chars.append(chr((ord(ch) + ord(key_ch)) % 256))

    joined = "".join(encoded_chars).encode("utf-8")
    return base64.urlsafe_b64encode(joined).decode("ascii")


def decode_mask(secret: str, encoded: str) -> str:
    """
    Decode an encoded string using the provided secret.
    """
    if encoded is None:
        return ""
    secret = (secret or "").strip()
    if not secret:
        return encoded

    try:
        decoded_bytes = base64.urlsafe_b64decode(encoded.encode("ascii"))
        decoded = decoded_bytes.decode("utf-8")
    except Exception:
        # Fallback to the raw encoded string if decoding fails
        return encoded

    decoded_chars: list[str] = []
    secret_len = len(secret)
    for idx, ch in enumerate(decoded):
        key_ch = secret[idx % secret_len]
        decoded_chars.append(chr((256 + ord(ch) - ord(key_ch)) % 256))

    return "".join(decoded_chars)


def obfuscate_mask_tokens(tokens: Iterable[dict], secret: str | None) -> list[dict]:
    """
    Return a new list of tokens where any @m / ~m tokens have their payload encoded.
    The encoded tokens are marked with `\"masked\": True` so they can be decoded later.
    """
    secret = (secret or "").strip()
    if not secret:
        return list(tokens)

    obfuscated: list[dict] = []
    for token in tokens:
        new_token = dict(token)
        if _is_mask_token(new_token):
            token_text = new_token.get("token") or ""
            prefix, payload = _split_token_payload(token_text)
            if payload:
                new_token["token"] = f"{prefix} {encode_mask(secret, payload)}"
                new_token["masked"] = True
        obfuscated.append(new_token)
    return obfuscated


def reveal_mask_tokens(tokens: Iterable[dict], secret: str | None) -> list[dict]:
    """
    Return a new list of tokens where encoded mask payloads have been decoded.
    Tokens that are not marked as `masked` are returned untouched.
    """
    secret = (secret or "").strip()
    revealed: list[dict] = []
    for token in tokens or []:
        new_token = dict(token)
        if not secret or not new_token.get("masked"):
            revealed.append(new_token)
            continue

        token_text = new_token.get("token") or ""
        prefix, payload = _split_token_payload(token_text)
        if not payload:
            revealed.append(new_token)
            continue
        new_token["token"] = f"{prefix} {decode_mask(secret, payload)}"
        revealed.append(new_token)
    return revealed


def _is_mask_token(token: dict) -> bool:
    key = token.get("k") or token.get("key")
    return key in MASK_TOKEN_KEYS


def _split_token_payload(token_text: str) -> tuple[str, str]:
    """
    Split a token string of the form '@m value' into ('@m', 'value').
    Returns (token_text, '') if no whitespace separator is present.
    """
    if not token_text:
        return "", ""
    try:
        idx = token_text.index(" ")
    except ValueError:
        return token_text, ""
    return token_text[:idx], token_text[idx + 1 :]
