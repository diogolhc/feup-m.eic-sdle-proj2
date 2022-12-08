"""Utility functions to validate and parse inputs, for example command arguments."""
import ipaddress

class PortValidator:
    """Validates and parses a port."""
    @staticmethod
    def port(s):
        port = int(s)
        if port < 1 or port > 65535:
            raise ValueError
        return port


class IpValidator:
    @staticmethod
    def ip_address(s):
        """Validates and parses an ip address."""
        ipaddress.ip_address(s)
        return s


class IpPortValidator:
    def __init__(self, default_port=None):
        self.default_port = default_port

    def ip_address(self, s):
        """Validates and parses an ip:port pair."""
        parts = str(s).split(':')

        if len(parts) == 1:
            if self.default_port is None:
                raise ValueError
            port = self.default_port
        elif len(parts) == 2:
            port = PortValidator.port(parts[1])
        else:
            raise ValueError
        
        ip = IpValidator.ip_address(parts[0])

        return (ip, port)

class PositiveIntegerValidator:
    @staticmethod
    def positive_integer(s):
        """Validates and parses a positive integer."""
        i = int(s)
        if i <= 0:
            raise ValueError
        return i
