"""A userid is a combination of an IP address and the public port of a node."""
from src.validator import IpPortValidator


class User:
    def __init__(self, userid):
        self.ip = userid[0]
        self.port = userid[1]

    @staticmethod
    def from_str(s):
        return User(IpPortValidator().ip_address(s))

    @staticmethod
    def from_filename(s):
        return User(IpPortValidator().ip_address(s.replace("-", ":")))

    def to_filename(self):
        return f"{self.ip}-{self.port}"

    def __str__(self):
        return f"{self.ip}:{self.port}"

    def __eq__(self, other):
        return self.ip == other.ip and self.port == other.port
