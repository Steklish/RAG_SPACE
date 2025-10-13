# app/mcp/main.py

from fastapi import FastAPI
from app.mcp.controller.database_controller import router as database_router

app = FastAPI()

app.include_router(database_router, prefix="/api/database")


@app.get("/")
async def root():
    return {"message": "Database API is running"}
