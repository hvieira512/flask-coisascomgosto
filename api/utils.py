import re

EMAIL_REGEX = re.compile(
    r"([A-Za-z0-9]+[._-])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Za-z]{2,})+"
)


def is_email_valid(email: str) -> bool:
    return bool(EMAIL_REGEX.fullmatch(email))
