from config import db, bcrypt

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(80), unique = True, nullable = False)
    password = db.Column(db.String(80), unique = False, nullable = False)

    @staticmethod
    def hash_password(password):
        return bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    # Chequear, capaz habria que poner algun atributo mas
    def to_json(self):
        return{
            "id": self.id,
            "username": self.user,
            #"password": self.password,
        }
