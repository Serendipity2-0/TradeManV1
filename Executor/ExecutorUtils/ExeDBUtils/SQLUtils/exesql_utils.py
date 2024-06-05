import sqlite3
import pandas as pd
import glob
import os


def db_to_excel(db_folder_path, output_folder):
    """
    Convert all SQLite database files in a folder to Excel files.

    Args:
        db_folder_path (str): The path to the folder containing the .db files.
        output_folder (str): The path to the folder where the .xlsx files will be saved.

    Returns:
        None
    """
    # Find all .db files in the specified folder
    db_files = glob.glob(os.path.join(db_folder_path, "*.db"))

    for db_file in db_files:
        # Establish a connection to the database
        conn = sqlite3.connect(db_file)

        # Get a list of all tables in the database
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables = pd.read_sql_query(query, conn)["name"].tolist()

        # Prepare the path for the output Excel file
        excel_file = os.path.join(
            output_folder, os.path.splitext(os.path.basename(db_file))[0] + ".xlsx"
        )

        with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
            for table in tables:
                # Read the table into a pandas DataFrame
                df = pd.read_sql_query(f"SELECT * FROM {table}", conn)

                # Export the DataFrame to an Excel sheet named after the table
                df.to_excel(writer, sheet_name=table, index=False)

        # Close the connection to the database
        conn.close()
        print(f"Exported {db_file} to {excel_file}")


def excel_to_db(excel_folder_path, output_folder):
    """
    Convert all Excel files in a folder to SQLite database files.

    Args:
        excel_folder_path (str): The path to the folder containing the .xlsx files.
        output_folder (str): The path to the folder where the .db files will be saved.

    Returns:
        None
    """
    # Find all .xlsx files in the specified folder
    excel_files = glob.glob(os.path.join(excel_folder_path, "*.xlsx"))

    for excel_file in excel_files:
        # Create a new SQLite database file for each Excel file
        db_file = os.path.join(
            output_folder, os.path.splitext(os.path.basename(excel_file))[0] + ".db"
        )

        # Establish a connection to the new database
        conn = sqlite3.connect(db_file)

        # Read each sheet from the Excel file into a DataFrame and write it to the database
        xls = pd.ExcelFile(excel_file)
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            df.to_sql(sheet_name, conn, index=False, if_exists="replace")

        # Close the connection to the database
        conn.close()
        print(f"Converted {excel_file} to {db_file}")


db_folder_path = ""
excel_folder = ""

# Run the function
db_to_excel(db_folder_path, excel_folder)
excel_to_db(excel_folder, db_folder_path)
