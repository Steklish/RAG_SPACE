# mcps/explore_database.py

# Import necessary libraries (e.g., for database interaction)
# For PostgreSQL:
import psycopg2
import os

# Install psycopg2: pip install psycopg2

# Replace with your database connection details
# For PostgreSQL:
# Retrieve connection parameters from environment variables
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "your_db")
DB_USER = os.environ.get("DB_USER", "your_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "your_password")
DB_PORT = os.environ.get("DB_PORT", "5432")  # Default PostgreSQL port


try:
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    print("Connected to PostgreSQL")
except psycopg2.Error as e:
    print(f"Error connecting to PostgreSQL: {e}")
    conn = None


# Function to execute read-only queries
def explore_database(query):
    """Executes a read-only SQL query and returns the results.

    Args:
        query: The SQL query to execute.

    Returns:
        A list of tuples representing the query results, or None on error.
    """
    try:
        if conn is None:
            print("Not connected to the database.")
            return None
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        return results
    except Exception as e:
        print(f"Error executing query: {e}")
        return None


if __name__ == "__main__":
    # Example usage:
    # Replace with your actual query
    sql_query = "SELECT * FROM your_table LIMIT 10;"  # Replace 'your_table' with your table name
    results = explore_database(sql_query)

    if results:
        print("Query results:")
        for row in results:
            print(row)
    else:
        print("No results found.")

    if conn:
        conn.close()
        print("Connection closed.")
