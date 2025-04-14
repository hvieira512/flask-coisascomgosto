from flask import jsonify

import pyodbc
import os


def get_db_connection():
    """Create and return a new database connection and cursor."""
    driver = os.getenv("DB_DRIVER")
    server = os.getenv("DB_SERVER")
    db = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    pwd = os.getenv("DB_PASS")

    db_conn = f"DRIVER={{{driver}}};SERVER={server};DATABASE={db};UID={user};PWD={pwd}"

    conn = pyodbc.connect(db_conn)
    return conn, conn.cursor()


def fetch_one(query, params=()):
    """Helper function to execute a query and fetch one result."""
    conn, cursor = get_db_connection()
    try:
        cursor.execute(query, params)
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def fetch_all(query, params=()):
    """Helper function to execute a query and fetch all results."""
    conn, cursor = get_db_connection()
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def execute(query, params=()):
    """Helper function to execute insert, update, or delete queries."""
    conn, cursor = get_db_connection()
    try:
        cursor.execute(query, params)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def execute_many(query, params=()):
    """Helper function that inserts multiple rows at once."""
    conn, cursor = get_db_connection()
    try:
        cursor.executemany(query, params)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def validate_json_fields(data, required_fields):
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid or missing JSON body."}), 400

    errors = {}

    for field, expected_type in required_fields.items():
        if field not in data:
            errors[field] = f"Missing (expected type: {expected_type.__name__})"
        elif not isinstance(data[field], expected_type):
            errors[field] = (
                f"Wrong type: expected {expected_type.__name__}, got {type(data[field]).__name__}"
            )

    if errors:
        return jsonify({"error": "There are missing fields", "fields": errors}), 400

    return None
