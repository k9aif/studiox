import yaml
import psycopg2
from psycopg2.extras import RealDictCursor

def load_config():
    with open("k9_aif_abb/config/config.yaml", "r") as f:
        return yaml.safe_load(f)

def test_connection():
    config = load_config()
    db = config["postgres"]

    try:
        print("Connecting to PostgreSQL...")

        conn = psycopg2.connect(
            host=db["host"],
            port=db["port"],
            user=db["user"],
            password=db["password"],
            dbname=db["database"]
        )

        print("Connection successful")

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Set schema explicitly
        schema = db.get("schema", "public")
        cursor.execute(f"SET search_path TO {schema};")

        print(f"Using schema: {schema}")

        # Test query
        cursor.execute("SELECT now();")
        result = cursor.fetchone()

        print("Database time:", result["now"])

        # Check tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s;
        """, (schema,))

        tables = cursor.fetchall()

        print("\nTables found:")
        for t in tables:
            print(f" - {t['table_name']}")

        cursor.close()
        conn.close()

        print("\nDatabase test completed successfully")

    except Exception as e:
        print("Database connection failed")
        print(str(e))


if __name__ == "__main__":
    test_connection()