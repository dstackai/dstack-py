__version__ = "0.4.0"


def version_to_int(version: str) -> int:
    parts = [int(x, 10) for x in version.split('.')]
    parts.reverse()
    return sum(x * (10 ** i) for i, x in enumerate(parts))
