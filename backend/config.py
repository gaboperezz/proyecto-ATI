from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import os

# import secrets
# clave_jwt = secrets.token_hex(32)


app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mssql+pyodbc://gabo:1357@localhost/db_prueba?driver=ODBC+Driver+17+for+SQL+Server"
    ) # #Aca va el link de la base de datos

# # CONEXION BD #
# server = 'proyecto-303361-288901.database.windows.net'
# bd = 'proyecto-303361-288901'
# user = 'db_manager'
# contrasena = 'RV71ok9%"5Og'

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['JWT_SECRET_KEY'] = 'mi_CLAVE' #ver que onda esto
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), 'uploads')


db = SQLAlchemy(app)
bcrypt = Bcrypt()