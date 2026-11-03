from uuid import UUID

# Loopback-only single-user demo identity, never accepted from request payloads.
DEMO_USER_ID = UUID("00000000-0000-4000-8000-000000000001")


def get_current_user() -> UUID:
    return DEMO_USER_ID
