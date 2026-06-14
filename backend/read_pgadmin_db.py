import sqlite3
import os

def read_db():
    db_path = r"C:\Users\hroya\AppData\Roaming\pgAdmin\pgadmin4.db"
    if not os.path.exists(db_path):
        print("pgadmin4.db not found!")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check available tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]
        print("Tables in pgadmin4.db:", tables)
        
        if 'server' in tables:
            cursor.execute("SELECT id, name, host, port, username, password FROM server;")
            rows = cursor.fetchall()
            print("\nSaved Servers in pgAdmin:")
            for row in rows:
                print(f"ID: {row[0]}, Name: {row[1]}, Host: {row[2]}, Port: {row[3]}, Username: {row[4]}, Encrypted Password: {row[5]}")
        else:
            print("Table 'server' not found.")
            
        conn.close()
    except Exception as e:
        print(f"Error reading pgadmin4.db: {e}")

if __name__ == "__main__":
    read_db()
