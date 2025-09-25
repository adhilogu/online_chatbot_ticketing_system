import sqlite3
import csv
import os


def sqlite_to_csv(sqlite_file, output_directory):
    """
    Convert SQLite database tables to CSV files.

    :param sqlite_file: Path to the SQLite database file.
    :param output_directory: Directory where CSV files will be saved.
    """
    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Connect to SQLite database
    conn = sqlite3.connect(sqlite_file)
    cursor = conn.cursor()

    try:
        # Get the list of all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        for table_name in tables:
            table_name = table_name[0]
            csv_file_path = os.path.join(output_directory, f"{table_name}.csv")

            # Fetch all data from the table
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            # Get column names
            column_names = [description[0] for description in cursor.description]

            # Write to CSV file
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(column_names)  # Write header
                writer.writerows(rows)  # Write data rows

            print(f"Table '{table_name}' has been exported to {csv_file_path}.")
    finally:
        # Close the connection
        conn.close()


# Example usage
sqlite_file = "db.sqlite3"  # Replace with your SQLite database file
output_directory = "output_csv"  # Directory to save CSV files
sqlite_to_csv(sqlite_file, output_directory)
