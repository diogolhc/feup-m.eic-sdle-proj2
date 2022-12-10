"""Abstracts sending a request to a given IP and Port, assuming that the data and response are dictionaries serialized to JSON."""
import asyncio
import json
import logging

log = logging.getLogger('timeline')

async def request(data, ip, port):
    reader, writer = await asyncio.open_connection(ip, port)

    log.debug("Sending message: %s", data)
    writer.write(json.dumps(data).encode())
    writer.write_eof()
    await writer.drain()
    
    data = await reader.read()
    response = json.loads(data.decode())
    log.debug("Received message: %s from %s:%s", response, ip, port)
    writer.close()
    await writer.wait_closed()

    return response
