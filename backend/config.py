from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_bcrypt import Bcrypt


# import secrets
# clave_jwt = secrets.token_hex(32)


app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mibasededatos.db" #Aca va el link de la base de datos
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['JWT_SECRET_KEY'] = 'chelin123'

db = SQLAlchemy(app)
bcrypt = Bcrypt()