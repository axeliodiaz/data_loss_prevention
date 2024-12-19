import re


def scan_message(message, patterns):
    """
    Scans a message for matches against a list of patterns.

    Args:
        message (str): The message to scan.
        patterns (list): List of objects with `regex` attributes.

    Returns:
        list: List of matching patterns.
    """
    matches = []
    for pattern in patterns:
        if re.search(pattern.regex, message):
            matches.append(pattern)
    return matches
