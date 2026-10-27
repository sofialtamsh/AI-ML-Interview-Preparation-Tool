class UserFacingError(Exception):
    """An error whose message is safe to show to admins: it never contains secrets or internals."""
