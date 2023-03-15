from typing import List, Optional, Union

from fastapi import FastAPI
from pydantic import BaseModel

from ethjsonrpc.client import Client

app = FastAPI()
client = Client()


class Payload(BaseModel):
    jsonrpc: str
    method: str
    params: Optional[list]
    id: int


class Result(BaseModel):
    id: int
    jsonrpc: str
    result: Union[dict, List[str], str]


@app.post("/")
async def main(payload: Payload) -> Result:
    return Result(
        id=payload.id,
        jsonrpc=payload.jsonrpc,
        result=await getattr(client, payload.method)(*(payload.params or [])),
    )
