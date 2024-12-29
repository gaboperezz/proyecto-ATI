#Importar libreria para manejo de la db#
import pyodbc

from flask import request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from config import app, db
from models import User, Document, Keyword, SearchResult, Search
from datetime import datetime, timezone
import os

import re
from tkinter import filedialog
from pdfminer.high_level import extract_pages, extract_text
from pdfminer.layout import LTTextContainer

#
usuarioLogueado = None
palabrasClave = {} 
#


# # UPLOAD FILE

@app.route('/upload', methods=['POST'])
def upload_file():
    # Obtener el archivo y el ID del usuario desde la solicitud
    file = request.files.get('document')
    user_id = request.form.get('user_id')  # Asegúrate de que el formulario incluya este campo.

    if not file or not user_id:
        return jsonify({"error": "Archivo y usuario son obligatorios."}), 400

    # Generar la ruta completa del archivo
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)

    try:
        # Guardar el archivo en el sistema de archivos
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Crear el directorio si no existe
        file.save(file_path)

        # Guardar información en la base de datos
        new_document = Document(
            user_id=user_id,
            filename=file.filename,
            file_path=file_path,
            uploaded_at=datetime.now(timezone.utc)
        )
        db.session.add(new_document)
        db.session.commit()

        return jsonify({"message": "Archivo subido con éxito.", "document_id": new_document.id}), 201

    except Exception as e:
        # Manejar errores y revertir la transacción en caso de fallo
        db.session.rollback()
        return jsonify({"error": "Error al subir el archivo.", "details": str(e)}), 500


# RUTAS DE LA API

@app.route("/")
def index():
    return "<h1>Hola world<h1>"

@app.route("/usuarios", methods=["GET"])
def get_usuarios():
    users = User.query.all()
    json_users = list(map(lambda x: x.to_json(), users))
    return jsonify({"usuarios": json_users}) #Aca manda codigo 200 por default

@app.route("/crear_usuario", methods=["POST"])
def crear_usuario():
    user = request.json.get("username")
    password = request.json.get("password")

    if not user or not password:
        return (
            jsonify({"message": "Las credenciales no pueden estar vacías."}),
            400
        )
    
    if User.query.filter_by(username=user).first():
        return jsonify({"error": "El usuario ya existe"}), 400
    
    hashed_password = User.hash_password(password)
    nuevo_usuario = User(username=user, password=hashed_password)
    
    try:
        db.session.add(nuevo_usuario)
        db.session.commit()
    except Exception as e:
        return (
            jsonify({"message": str(e)}),
            400
        )

    return jsonify({"message": "Usuario creado!"}), 201


@app.route("/actualizar_usuario/<int:user_id>", methods=["PATCH"]) #capaz tenemos que cambiarlo por PUT
def actualizar_usuario(user_id):
    usuario = User.query.get(user_id)

    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404
    
    data = request.json
    usuario.user = data.get("username", usuario.user)
    usuario.password = data.get("password", usuario.password)

    db.session.commit()

    return jsonify({"message": "Usuario actualizado"}), 201


@app.route("/borrar_usuario/<int:user_id>", methods=["DELETE"])  
def borrar_usuario(user_id):
    usuario = User.query.get(user_id) 
    
    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404
    
    db.session.delete(usuario)
    db.session.commit()

    return jsonify({"message": "Usuario borrado"}), 200


@app.route("/login", methods=["POST"])
def login():

    data = request.json
    user = data.get("username")
    password = data.get("password")

    usuario = User.query.filter_by(username=user).first()
    
    if not usuario or not usuario.check_password(password):
        return jsonify({"message": "Las credenciales son incorrectas"}), 401

    token = create_access_token(identity=user.id)
    return jsonify({"token": token}), 200


def openFile():
    filepath = filedialog.askopenfilename()
    archivo = open(filepath, 'rb')
    text = extract_text(archivo)
    #print(text)

# Registrar palabras clave#
def agregarPalabrasClave():
    filepath = filedialog.askopenfilename() 
    with open(filepath, 'r', encoding='utf-8') as archivo:  # Abre el archivo en modo texto
        texto = archivo.read() 
        print(texto)
        # Separar las frases por comas
        palabras = re.split(r',\s*', texto)
        for palabra in palabras:
            # No sirve el código: palabrasClave[palabra] = 1 porque sobreescribe lo anterior
            palabrasClave.setdefault(palabra, 1)
        print(palabrasClave)

def eliminarPalabrasClave():
    palabraABorrar = entryPrograma.get().strip()
    if palabraABorrar in palabrasClave:
        del palabrasClave[palabraABorrar]  # Elimina la palabra del diccionario
        print(f"'{palabraABorrar}' fue eliminada del diccionario.")
    else:
        print(f"'{palabraABorrar}' no se encontró en el diccionario.\n Palabras clave:")
        print(palabrasClave)


def encontrarPalabrasClaveEnTextoPorPagina(filepath):
    with open(filepath, 'rb') as archivo:
        for page_number, page_layout in enumerate(extract_pages(archivo), start=1):
            page_text = ""
            for element in page_layout:
                 if isinstance(element, LTTextContainer):  # Solo procesar elementos de texto
                    page_text += element.get_text()


            # Dividir en párrafos por página
            parrafos = [p.strip() for p in page_text.split('\n') if p.strip()]

            parrafos_procesados = []
            i = 0
            while i < len(parrafos):
                if parrafos[i].endswith('-') and i + 1 < len(parrafos):  # Si el párrafo termina con guión

                    primeraPalabraSiguiente = devolverPrimeraPalabraParrafo(parrafos[i + 1]) 
                    ultimaPalabraActual = devolverUltimaPalabraParrafo(parrafos[i])

                    ultimaPalabraSinGuion = ultimaPalabraActual[:-1]
                    ultimaPalabraSinGuion += primeraPalabraSiguiente
                    
                    # agregar la palabra al primer parrafo y sacarla del segundo
                    parrafos[i] = parrafos[i][:-len(ultimaPalabraActual)] + ultimaPalabraSinGuion

                    # Eliminar la primera palabra del siguiente párrafo
                    parrafos[i + 1] = ' '.join(parrafos[i + 1].split()[1:])  # Quitar la primera palabra del siguiente párrafo

                parrafos_procesados.append(parrafos[i])

                i += 1


            # Buscar palabras clave en los párrafos
            for palabra in palabrasClave:
                # Expresión regular para buscar la palabra completa
                pattern = rf'\b{re.escape(palabra)}\b'
                encontrada = False

                for i, parrafo in enumerate(parrafos, start=1):
                    matches = re.findall(pattern, parrafo, flags=re.IGNORECASE)
                    count = len(matches)
                   

                    if count > 0:
                        if not encontrada:
                            ##print(f"EL PARRAFO NUMERO {i} DICE: " + parrafo)
                            print(f"\nPalabra clave: '{palabra}' encontrada en la página {page_number}, párrafo {i}")
                            print(f"El parrafo dice:  {parrafo}")
                            encontrada = True

def devolverPrimeraPalabraParrafo(parrafo):

    palabras = parrafo.split()

    return palabras[0] if palabras else None

def devolverUltimaPalabraParrafo(parrafo):

    palabras = parrafo.split()

    return palabras[-1] if palabras else None


# # CONEXION BD #
# server = 'localhost\SQLEXPRESS'
# #proyecto-303361-288901.database.windows.net#
# bd = 'db_prueba'
# #proyecto-303361-288901#
# user = 'gabo'
# #db_manager#
# contrasena = '1357'
# #RV71ok9%"5Og#

# try:
#     conexion = pyodbc.connect('DRIVER={SQL Server}; SERVER=' + server + 
#                 ';DATABASE=' + bd + ';UID=' + user + ';PWD=' + contrasena)

#     print("funcionaa :)")
# except pyodbc.Error as e:
#     print("Error de conexión:", e)

# PARA QUE FUNCIONE LA APLICACION

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        jwt = JWTManager(app)

    app.run(debug=True)
