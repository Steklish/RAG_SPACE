# app/mcp/controller/database_controller.py
from fastapi import APIRouter, HTTPException
from typing import List, Tuple, Optional
from app.mcp.model.database_model import DatabaseModel

router = APIRouter()

model = DatabaseModel()

def is_safe_query(query: str) -> bool:
    """
    Checks if the query is a SELECT statement and doesn't contain any harmful keywords.
    """
    query = query.strip().lower()
    if query.startswith("select"):
        # Add more checks for potentially harmful keywords or patterns
        if "insert" in query or "update" in query or "delete" in query or "drop" in query or "alter" in query:
            return False
        return True
    return False


@router.get("/query")
async def execute_query(query: str):
    if not is_safe_query(query):
        raise HTTPException(status_code=400, detail="Query is not safe. Only SELECT queries are allowed.")

    model.connect()
    results = model.execute_query(query)
    model.disconnect()
    if results is None:
        raise HTTPException(status_code=500, detail="Error executing query")
    return {"results": results}

@router.get("/tables")
async def list_tables():
    model.connect()
    table_columns = model.get_table_columns()
    model.disconnect()
    if table_columns is None:
        raise HTTPException(status_code=500, detail="Error listing tables")
    return {"tables": table_columns}