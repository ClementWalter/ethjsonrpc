import json
import logging
from typing import List, Optional, Union

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware import Middleware
from pydantic import BaseModel
from starlette.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ethjsonrpc.constants import GATEWAY_URL
from ethjsonrpc.eth_client import EthClient

load_dotenv()

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class RequestContextLogMiddleware(BaseHTTPMiddleware):
    async def set_body(self, request: Request):
        receive_ = await request._receive()

        async def receive():
            return receive_

        request._receive = receive

    async def dispatch(self, request: Request, call_next):
        await self.set_body(request)
        body = await request.json()
        logger.debug(f"RPC request:\n\t{body}")
        response = await call_next(request)
        response_body = [chunk async for chunk in response.body_iterator]
        response.body_iterator = iterate_in_threadpool(iter(response_body))
        logger.debug(f"RPC response:\n\t{json.loads(response_body[0].decode())}")
        return response


middleware = [Middleware(RequestContextLogMiddleware)]
app = FastAPI(middleware=middleware)


@app.on_event("startup")
async def get_client():
    global eth_client
    eth_client = await EthClient.new(GATEWAY_URL)


class Payload(BaseModel):
    jsonrpc: str
    method: str
    params: Optional[list]
    id: int


class Result(BaseModel):
    id: int
    jsonrpc: str
    result: Union[dict, List[str], str, int]


@app.post("/")
async def main(payload: Payload) -> Result:
    if not hasattr(eth_client, payload.method):
        raise NotImplementedError(f"{payload.method}({','.join(payload.params or [])})")
    return Result(
        id=payload.id,
        jsonrpc=payload.jsonrpc,
        result=await getattr(eth_client, payload.method)(*(payload.params or [])),
    )
