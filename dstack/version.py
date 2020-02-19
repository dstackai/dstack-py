class Version(object):
    def __init__(self, major: int, minor: int, patch: int):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __repr__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
