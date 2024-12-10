import sqlite3
import sys

def inspect_sqlite_db(db_path):
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("Tables found in database:")
        for table in tables:
            print(f"\nTable: {table[0]}")
            # Get schema for each table
            cursor.execute(f"PRAGMA table_info('{table[0]}')")
            columns = cursor.fetchall()
            print("Columns:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM '{table[0]}'")
            count = cursor.fetchone()[0]
            print(f"Row count: {count}")
            
            # Sample data (first row)
            if count > 0:
                cursor.execute(f"SELECT * FROM '{table[0]}' LIMIT 1")
                sample = cursor.fetchone()
                print("Sample row:")
                print(f"  {sample}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    db_path = "Data/financial_data.db"
    inspect_sqlite_db(db_path)
