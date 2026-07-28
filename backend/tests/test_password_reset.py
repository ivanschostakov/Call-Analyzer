from src.app.modules.auth.router import hash_password_reset_token
from src.app.modules.auth.schemas import PasswordResetConfirmPayload


def test_password_reset_token_hash_is_stable_and_does_not_expose_token() -> None:
    token = "secret-reset-token"
    token_hash = hash_password_reset_token(token)

    assert token_hash == hash_password_reset_token(token)
    assert token not in token_hash
    assert len(token_hash) == 64


def test_password_reset_password_validation() -> None:
    payload = PasswordResetConfirmPayload(
        token="x" * 32,
        new_password="new-password",
    )

    assert payload.new_password == "new-password"
