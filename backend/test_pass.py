import psycopg2

PASSWORDS = [
    'Him@2026', 'him@2026', 'Himanshu@2026', 'himanshu@2026',
    'Hroya@2026', 'hroya@2026', 'Himanshu2026', 'himanshu2026',
    'Hroya2026', 'hroya2026', 'Him@2025', 'him@2025', 'Himanshu@2025',
    'himanshu@2025', 'Hroya@2025', 'hroya@2025', 'Himanshu2025', 'himanshu2025',
    'Hroya2025', 'hroya2025', '0000', '1111', '1234567'
]

def test():
    for p in PASSWORDS:
        try:
            print(f"Testing: '{p}'")
            con = psycopg2.connect(
                dbname='postgres',
                user='postgres',
                password=p,
                host='localhost',
                port='5432',
                connect_timeout=2
            )
            con.close()
            print(f"FOUND WORKING PASSWORD: '{p}'")
            return
        except Exception as e:
            if "password authentication failed" in str(e):
                continue
            else:
                print(f"Other error for '{p}': {e}")

if __name__ == "__main__":
    test()
