import pymysql
from platform_app.database.init_db import init_database

def reset_db():
    print("Dropping database 'lead_main'...")
    connection = pymysql.connect(
        host="localhost",
        port=3306,
        user="root",
        password="",
        charset="utf8mb4",
    )
    with connection.cursor() as cursor:
        cursor.execute("DROP DATABASE IF EXISTS lead_main")
    connection.close()
    print("Database dropped.")
    
    print("Creating all tables...")
    init_database()
    print("Database reset complete.")

if __name__ == "__main__":
    reset_db()
