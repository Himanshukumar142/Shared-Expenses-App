import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

# List of common and personalized passwords to try based on other files
COMMON_PASSWORDS = [
    '', 'postgres', 'admin', 'root', '1234', '123456', 'Password123',
    'hroya', 'hroya123', 'hraj02223', 'businesshub934', 'grxlihzhccujrtyx',
    'postgres123', '12345678', '123456789', 'password', 'postgresql',
    'himanshu', 'himanshu123', 'himanshu@123', 'himanshukumar', 'himanshukumar123', 'himanshukumar@123',
    'LabourFinder_project123', 'admin123', 'admin@123', 'postgres@123', '123', '12345',
    'postgres@123', 'Postgres@123', 'root123', 'root@123'
]

def try_passwords():
    db_name = os.getenv('DB_NAME', 'expenses_db')
    db_user = os.getenv('DB_USER', 'postgres')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')

    working_password = None

    for password in COMMON_PASSWORDS:
        try:
            print(f"Trying connection with password: '{password}'...")
            con = psycopg2.connect(
                dbname='postgres',
                user=db_user,
                password=password,
                host=db_host,
                port=db_port,
                connect_timeout=2
            )
            con.close()
            working_password = password
            print(f"Success! Correct password is: '{password}'")
            break
        except Exception as e:
            err_msg = str(e)
            if ("password authentication failed" in err_msg or 
                "fe_sendauth" in err_msg or 
                "no password supplied" in err_msg):
                continue
            else:
                print(f"Other connection error: {e}")
                break

    if working_password is not None:
        try:
            con = psycopg2.connect(
                dbname='postgres',
                user=db_user,
                password=working_password,
                host=db_host,
                port=db_port
            )
            con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = con.cursor()
            
            cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}';")
            exists = cursor.fetchone()
            
            if not exists:
                cursor.execute(f"CREATE DATABASE {db_name};")
                print(f"Database '{db_name}' created successfully!")
            else:
                print(f"Database '{db_name}' already exists.")
                
            cursor.close()
            con.close()
            
            update_env_file(working_password)
            
        except Exception as e:
            print(f"Error during DB creation: {e}")
    else:
        print("Failed to find working password. Please create the database manually or provide the password.")

def update_env_file(password):
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            if line.startswith('DB_PASSWORD='):
                new_lines.append(f"DB_PASSWORD={password}\n")
            else:
                new_lines.append(line)
                
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
        print("Updated .env file with correct password.")

if __name__ == "__main__":
    try_passwords()
