import sqlite3
import pandas as pd

def get_db_connection(db_path):
    """Create a database connection to the SQLite database specified by db_path."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as e:
        print(e)
    return conn

#dump the data from df to sqlite db
def dump_df_to_sqlite(df, table_name, conn):
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    print(f"Dumped {table_name} to SQLite database.")
    

