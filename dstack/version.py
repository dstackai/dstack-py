# FIXME: do we need to support PEP-0440 (https://www.python.org/dev/peps/pep-0440/)?
class Version(object):
    def __init__(self, major: int, minor: int, patch: int):
        self.major = major
        self.minor = minor
        self.patch = patch
