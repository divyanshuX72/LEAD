import pymysql
from platform_app.database.init_db import init_database

def reset_db():
    print("Dropping lead database...")
    connection = pymysql.connect(
        host="localhost",
        port=3306,
        user="root",
        password="",
        charset="utf8mb4",
    )
    with connection.cursor() as cursor:
        cursor.execute("DROP DATABASE IF EXISTS lead")
        cursor.execute("CREATE DATABASE lead CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    connection.close()
    print("Database recreated. Initializing tables...")
    init_database()
    print("Done!")

if __name__ == "__main__":
    reset_db()
