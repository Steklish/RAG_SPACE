# app/mcp/model/database_model.py

import os
import psycopg2
from typing import List, Tuple, Optional

class DatabaseModel:
    def __init__(self):
        self.conn = None

    def connect(self):
        # Retrieve connection parameters from environment variables
        DB_HOST = os.environ.get("DB_HOST", "localhost")
        DB_NAME = os.environ.get("DB_NAME", "your_db")
        DB_USER = os.environ.get("DB_USER", "your_user")
        DB_PASSWORD = os.environ.get("DB_PASSWORD", "your_password")
        DB_PORT = os.environ.get("DB_PORT", "5432")  # Default PostgreSQL port

        try:
            self.conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT
            )
            print("Connected to PostgreSQL")
        except psycopg2.Error as e:
            print(f"Error connecting to PostgreSQL: {e}")
            self.conn = None

    def disconnect(self):
        if self.conn:
            self.conn.close()
            print("Connection closed.")

    def execute_query(self, query: str) -> Optional[List[Tuple]]:
        if not self.conn:
            print("Not connected to the database.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                return results
        except Exception as e:
            raise Exception(f"Error executing query: {e}")
        
    def list_tables(self) -> Optional[List[str]]:
        if not self.conn:
            print("Not connected to the database.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                    """
                )
                tables = [row[0] for row in cursor.fetchall()]
                return tables
        except Exception as e:
            print(f"Error listing tables: {e}")
            return None
            
    def get_table_columns(self) -> Optional[dict]:
        if not self.conn:
            print("Not connected to the database.")
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT table_name, column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position;
                    """
                )
                results = cursor.fetchall()
                table_columns = {}
                for row in results:
                    table_name, column_name, data_type = row
                    if table_name not in table_columns:
                        table_columns[table_name] = []
                    table_columns[table_name].append({"column_name": column_name, "data_type": data_type})
                return table_columns
        except Exception as e:
            print(f"Error getting table columns: {e}")
            return None
