# db_connector.py
import mysql.connector
from mysql.connector import Error

def create_connection():
    """ Create a database connection to the MySQL database """
    connection = None
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="manoj",  # <-- CHANGE THIS to your MySQL username
            password="ssdiblr",  # <-- CHANGE THIS to your MySQL password
            database="hypeculture_db"
        )
        if connection.is_connected():
            # print("Successfully connected to the database")
            pass
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    return connection
