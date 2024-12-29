# import pyodbc

# conn = pyodbc.connect(
#     "DRIVER={ODBC Driver 17 for SQL Server};"
#     "SERVER=localhost;"
#     "DATABASE=db_prueba;"
#     "UID=gabo;"
#     "PWD=1357"
# )

# cursor = conn.cursor()
# cursor.execute("SELECT @@version;")
# row = cursor.fetchone()
# print(row)