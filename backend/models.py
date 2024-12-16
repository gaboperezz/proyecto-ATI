from config import db

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user = db.Column(db.String(80), unique = True, nullable = False)
    password = db.Column(db.String(80), unique = False, nullable = False)

    # Chequear, capaz habria que poner algun atributo mas
    def to_json(self):
        return{
            "id": self.id,
            "user": self.user,
            "password": self.password,
        } 
