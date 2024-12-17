from config import db, bcrypt
from datetime import datetime, timezone


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(80), unique = True, nullable = False)
    password = db.Column(db.String(80), unique = False, nullable = False)

    # Chequear, capaz habria que poner algun atributo mas
    def to_json(self):
        return{
            "id": self.id,
            "username": self.user,
        }


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relación con Document (1 Usuario -> N Documentos)
    documents = db.relationship("Document", backref="user", lazy="select")

    # Relación con Keyword (1 Usuario -> N Palabras clave)
    keywords = db.relationship("Keyword", backref="user", lazy="dynamic")

    # Relación con Search (1 Usuario -> N Búsquedas)
    searches = db.relationship("Search", backref="user", lazy="select")

    @staticmethod
    def hash_password(password):
        return bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.Text, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relación inversa automática creada con backref (user)


class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    keyword = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relación inversa automática creada con backref (user)


class Search(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.Text)
    search_date = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relación con SearchResult (1 Búsqueda -> N Resultados)
    results = db.relationship("SearchResult", backref="search", lazy="select")


class SearchResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    search_id = db.Column(db.Integer, db.ForeignKey('search.id'), nullable=False)
    keyword = db.Column(db.Text, nullable=False)
    occurrence_count = db.Column(db.Integer, default=0)

    # Relación inversa automática creada con backref (search)

