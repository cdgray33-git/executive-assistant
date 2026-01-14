"""
Generic IMAP connector placeholder (non-destructive).
For a production connector use IMAPClient or imaplib with OAuth2 where available.
Always implement a dry-run mode before destructive actions.
"""
def preview_messages(*a, **k):
    return []

def execute_move_to_trash(*a, **k):
    return {"moved_count": 0}
