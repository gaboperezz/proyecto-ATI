from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app, origins=["https://proyecto-perezulivi-b8atf7eqguhph3a4.azurewebsites.net"])

pwd = 'RV71ok9%"5Og'

DATABASE_URI = "mssql+pyodbc://db_manager:"+pwd+"@proyecto-303361-288901.database.windows.net/proyecto-303361-288901_v2?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"

# "mssql+pyodbc://db_manager:"+pwd+"@proyecto-303361-288901.database.windows.net/proyecto-303361-288901?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"

# "mssql+pyodbc://gabo:1357@GONZA\\SQLEXPRESS/db_prueba?driver=ODBC+Driver+17+for+SQL+Server" local gonza
# "mssql+pyodbc://gabo:1357@localhost/db_prueba?driver=ODBC+Driver+17+for+SQL+Server" local gabo

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI

# # CONEXION BD #
# server = 'proyecto-303361-288901.database.windows.net:1433?'
# bd = 'proyecto-303361-288901'
# user = 'db_manager'
# contrasena = 'RV71ok9%"5Og'

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['JWT_SECRET_KEY'] = 'sjF4V!0mElf#6n5$#dn*a!'
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), 'uploads')


db = SQLAlchemy(app)
bcrypt = Bcrypt()