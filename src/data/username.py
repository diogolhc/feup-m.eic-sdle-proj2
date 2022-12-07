"""A username is a combination of an IP address and the public port of a node."""
from src.validator import IpPortValidator

class Username:
    def __init__(self, username):
        self.ip = username[0]
        self.port = username[1]
    
    def from_str(s):
        return Username(IpPortValidator().ip_address(s))
    
    def from_filename(s):
        return Username(IpPortValidator().ip_address(s.replace('-', ':')))

    def to_filename(self):
        return f"{self.ip}-{self.port}"
    
    def __str__(self):
        return f"{self.ip}:{self.port}"
    
    def __eq__(self, other):
        return self.ip == other.ip and self.port == other.port
