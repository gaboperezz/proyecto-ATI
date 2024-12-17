from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import os

# import secrets
# clave_jwt = secrets.token_hex(32)


app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mibasededatos.db" #Aca va el link de la base de datos
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['JWT_SECRET_KEY'] = 'mi_CLAVE' #ver que onda esto
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), 'uploads')


db = SQLAlchemy(app)
bcrypt = Bcrypt()