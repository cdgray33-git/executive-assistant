"""
Gmail connector placeholder.
Real implementation should use Google OAuth2 and Gmail API (users must consent).
This placeholder is intentionally non-destructive and only simulates safe read-only operations.
"""
def preview_messages(*a, **k):
    return []

def delete_messages_dryrun(*a, **k):
    return {"candidates": []}
