from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="PingMe API",
    version="0.0.1"
)

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float

@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI application!"}

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}

@app.post("/items/")
async def create_item(item: Item):
    return item 