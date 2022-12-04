import json
import logging
import asyncio

log = logging.getLogger('timeline')

async def request(data, ip, port):
    reader, writer = await asyncio.open_connection(ip, port)

    log.debug("Sending message: %s", data)
    writer.write(json.dumps(data).encode())
    writer.write_eof()
    await writer.drain()
    
    data = await reader.read()
    response = json.loads(data.decode())
    log.debug("Received message: %s", response)
    writer.close()
    await writer.wait_closed()

    return response

class Response:
    def __init__(self, status, data=None):
        self.status = status
        self.data = data

    def to_dict(self):
        if self.data is None:
            return {"status": self.status}
        data = self.data.copy()
        data["status"] = self.status
        return data

class OkResponse(Response):
    def __init__(self, data=None):
        super().__init__("ok", data)

class ErrorResponse(Response):
    def __init__(self, message):
        super().__init__("error", {"error": message})
