from flask import request, jsonify, send_file
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from config import app, db
from models import User, Document, Keyword, SearchResult, Search
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
import os
import re
from pdfminer.high_level import extract_pages, extract_text
from pdfminer.layout import LTTextContainer
import pymupdf # Para usar fitz
import fitz 
import io
import deep_translator
from io import BytesIO

#
usuarioLogueado = None
palabrasClave = {} 
#

# RUTAS DE INTERES #

@app.route("/")
def index():
    return "<h1>Bienvenido<h1>"

@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify({"message": f"Hola, {current_user}. Esta es una ruta protegida!"}), 200


# LOGIN #
@app.route("/login", methods=["POST"])
def login():

    data = request.json
    user = data.get("username")
    password = data.get("password")

    usuario = User.query.filter_by(username=user).first()
    
    if not usuario or not usuario.check_password(password):
        return jsonify({"message": "Las credenciales son incorrectas"}), 401

    token = create_access_token(identity=str(usuario.id))
    usuario_logueado = usuario.id

    return jsonify({"token": token, "idUsuario":usuario_logueado}), 200

# REGISTRO #
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


# GET PALABRAS CLAVE DE UN USUARIO #
@app.route("/getPalabrasClave", methods=["GET"])
@jwt_required()
def get_palabras_clave_usuario():
    user_id = get_jwt_identity()
    try:
        # Obtener las palabras clave asociadas al usuario
        keywords = Keyword.query.filter_by(user_id=user_id).all()

        # Si no se encuentran palabras clave
        if not keywords:
            return jsonify({"message": "No se encontraron palabras clave para este usuario."}), 404

        # Retornar la lista de palabras clave
        keyword_list = [keyword.keyword for keyword in keywords]
        keyword_id_list = [keyword.id for keyword in keywords]
        return jsonify({"user_id": user_id, "keywords": keyword_list, "keywordsIds": keyword_id_list}), 200

    except Exception as e:
        return jsonify({"error": "Error al obtener las palabras clave.", "details": str(e)}), 500


# REGISTRO DE UNA PALABRA CLAVE #
@app.route("/crearPalabraClave", methods=["POST"])
@jwt_required()
def agregar_palabra_clave_usuario():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        palabra = data.get('word')
        
        # ??
        palabra.strip()
        
        if not palabra:
            return jsonify({"error": "La palabra clave es obligatoria."}), 400
        
        # No hay chequeo de palabras duplicadas
        # Pienso que si le ponemos unique al atributo, puede joder a las palabras clave de otros usuarios
        if Keyword.query.filter_by(keyword=palabra, user_id=user_id).first():
            return jsonify({"error": "El usuario ya registró esta palabra clave"}), 400

        nueva_keyword = Keyword(keyword=palabra, user_id=user_id)
        db.session.add(nueva_keyword)
        db.session.commit()

        return jsonify({"message": "Palabra clave agregada con éxito.", "word": palabra}), 201
    except Exception as e:
        return jsonify({"error": "Error al agregar la palabra clave.", "details": str(e)}), 500
    

# CARGAR ARCHIVO TXT DE PALABRAS CLAVE Y REGISTRARLAS #
@app.route("/upload/txt", methods=["POST"])
@jwt_required()
def cargar_txt_palabras_clave():
    
    try:
        # Obtener el usuario autenticado
        user_id = get_jwt_identity()

        # Validar que se haya enviado un archivo
        if 'file' not in request.files:
            return jsonify({"error": "No se envió ningún archivo."}), 400

        file = request.files['file']

        # Validar que el archivo tenga un nombre y sea un archivo .txt
        if file.filename == '':
            return jsonify({"error": "El archivo no tiene nombre."}), 400
        if not file.filename.endswith('.txt'):
            return jsonify({"error": "Solo se permiten archivos .txt."}), 400
        
        # Leer el contenido del archivo
        content = file.read().decode('utf-8')
        keywords = [keyword.strip() for keyword in content.split(',') if keyword.strip()]

        # Guardar palabras clave en la base de datos
        for word in keywords:
            new_keyword = Keyword(keyword=word, user_id=user_id)
            db.session.add(new_keyword)
        db.session.commit()

        return jsonify({
            "message": "Palabras clave cargadas exitosamente.",
            "keywords": keywords
        }), 201
    
    except Exception as e:
        return jsonify({"error": "Error al cargar las palabras clave.", "details": str(e)}), 500


# ELIMINAR PALABRA CLAVE #
# Recibe el id de una palabra para borrarla de la db
@app.route("/eliminarPalabraClave/<int:keyword_id>", methods=["DELETE"])
@jwt_required()
def eliminarPalabrasClave(keyword_id):

    palabraABorrar = Keyword.query.get(keyword_id)

    if not palabraABorrar:
        return jsonify({"message": "Palabra clave no encontrada"}), 404
    
    db.session.delete(palabraABorrar)
    db.session.commit()

    return jsonify({"message": "Palabra clave borrada"}), 200


# CARGA DE PDF #
@app.route('/upload/pdf', methods=['POST'])
@jwt_required()
def cargar_pdf():
    # Obtener el archivo y el ID del usuario desde la solicitud
    file = request.files.get('document')
    user_id = get_jwt_identity()  # Asegúrate de que el formulario incluya este campo.

    # Validar que se haya enviado un archivo
    if 'file' not in request.files:
        return jsonify({"error": "No se envió ningún archivo."}), 400
    
    file = request.files['file']

    # Validar que el archivo tenga un nombre y sea un PDF
    if file.filename == '':
        return jsonify({"error": "El archivo no tiene nombre."}), 400
    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "Solo se permiten archivos PDF."}), 400

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

        return jsonify({"message": "Archivo subido con éxito.", "idDocumento": new_document.id}), 201

    except Exception as e:
        # Manejar errores y revertir la transacción en caso de fallo
        db.session.rollback()
        return jsonify({"error": "Error al subir el archivo.", "details": str(e)}), 500
    
# Dividir el texto en fragmentos
def split_text(text, max_length=4999):
    """Divide el texto en fragmentos de longitud máxima 'max_length'."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

# Limpiar texto (eliminar caracteres no ASCII)
def clean_text(text):
    # Eliminar caracteres no ASCII y reemplazarlos con un espacio
    return re.sub(r'[^\x00-\x7F]+', '-', text)

# Función para extraer las tablas de un PDF
def extract_tables(pdf_path):
    tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
    return tables

# Función para traducir el PDF
@app.route('/translate/pdf', methods=['POST'])
@jwt_required()
def traducir_pdf():
    try:
        # Obtener los datos del formulario (el JSON enviado desde el front)
        data = request.json

        ids_documentos = data.get('idsDocumentos2')
        target_language = data.get('target_language', 'en')  # Idioma predeterminado: inglés

        # Validar que se haya enviado un ID de documento
        if not ids_documentos:
            return jsonify({"error": "Debes proporcionar los IDs de los documentos para la búsqueda."}), 400

        # Obtener los documentos desde la base de datos (o sistema de archivos) basados en los ids
        documents = Document.query.filter(Document.id.in_(ids_documentos)).all()
        if not documents:
            return jsonify({"error": "No se encontraron documentos válidos para el usuario."}), 404

        translated_pdf = fitz.open()  # Crear un nuevo PDF
        translator = deep_translator.GoogleTranslator(source='auto', target=target_language)

        # Traducir cada documento
        for document in documents:
            # Abrir el archivo PDF desde la ruta
            pdf_stream = open(document.file_path, 'rb')  
            pdf_document = fitz.open(pdf_stream)

            # Extraer las tablas del PDF original
            tables = extract_tables(document.file_path)

            # Traducir cada página
            for page_number in range(len(pdf_document)):
                page = pdf_document.load_page(page_number)
                text = page.get_text()

                # Dividir el texto en fragmentos de hasta 5000 caracteres
                text_fragments = split_text(text)

                translated_text = ""
                
                # Traducir cada fragmento
                for fragment in text_fragments:
                    clean_fragment = clean_text(fragment)  # Limpiar el texto antes de traducir
                    translated_text += translator.translate(clean_fragment)

                padding_x = 20  # Margen izquierdo y derecho
                padding_y = 30  # Margen superior e inferior

                # Crear una nueva página en el PDF traducido
                rect = page.rect  # Tamaño de la página original
                new_page = translated_pdf.new_page(width=rect.width, height=rect.height)

                # Calcular las coordenadas iniciales con margen
                x_start = rect.x0 + padding_x
                y_start = rect.y0 + padding_y

                # Asegurarse de que el texto traducido no exceda los límites de la página
                max_width = rect.width - 2 * padding_x
                max_height = rect.height - 2 * padding_y

                # Insertar el texto traducido en la nueva página respetando el margen
                new_page.insert_textbox(
                    fitz.Rect(x_start, y_start, x_start + max_width, y_start + max_height),
                    translated_text,
                    fontsize=12,
                    align=0  # Alinear el texto a la izquierda (opcional)
                )

                # Si hay tablas para esta página, insertarlas en la nueva página
                for table in tables:
                    # Verificar si la tabla está en la página actual
                    if table.page == page_number + 1:  # camelot usa una indexación de páginas basada en 1
                        table_data = table.df

                        # Verificar que table_data sea un DataFrame y que tenga filas
                        if isinstance(table_data, pd.DataFrame):
                            for _, row in table_data.iterrows():
                                # Convertir cada celda a cadena y unirlas
                                row_text = " | ".join(str(cell) for cell in row)
                                table_text = row_text + "\n"

                                # Determinar la posición de la tabla en la página
                                table_rect = fitz.Rect(x_start, y_start + max_height + padding_y, x_start + max_width, y_start + max_height + 200)
                                new_page.insert_textbox(table_rect, table_text, fontsize=10)

            pdf_document.close()  # Cerrar el documento después de traducir

        # Guardar el nuevo PDF en memoria
        output_stream = BytesIO()
        translated_pdf.save(output_stream)
        translated_pdf.close()

        # Enviar el PDF traducido como respuesta
        output_stream.seek(0)
        return send_file(
            output_stream,
            as_attachment=True,
            download_name="translated_document.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        print(str(e))
        return jsonify({"error": "Error al traducir el archivo PDF.", "details": str(e)}), 500

# OBTENER DOCUMENTOS DEL USUARIO #
@app.route('/user/documentos', methods=['GET'])
@jwt_required()
def get_documentos_usuario():
    try:
        user_id = get_jwt_identity()
        documents = Document.query.filter_by(user_id=user_id).all()
        document_list = [{"id": doc.id, "name": doc.filename} for doc in documents]

        return jsonify({"documents": document_list}), 200
    except Exception as e:
        return jsonify({"error": "Error al obtener documentos del usuario.", "details": str(e)}), 500


# OBTENER BUSQUEDAS REALIZADAS


# REALIZAR BUSQUEDA #
@app.route("/busqueda", methods=["POST"])
@jwt_required()
def realizar_busqueda():
    try:
        user_id = get_jwt_identity()
        data = request.json

        ids_documentos = data.get('idsDocumentos')
        nombre_busqueda = data.get('nombreBusqueda') #, 'Búsqueda sin nombre'

        if not ids_documentos:
            return jsonify({"error": "Debes proporcionar los IDs de los documentos para la búsqueda."}), 400
    
        if not nombre_busqueda:
            return jsonify({"error": "El nombre de la búsqueda es obligatorio."}), 400

        # Verificar que los documentos pertenecen al usuario
        documents = Document.query.filter(Document.id.in_(ids_documentos), Document.user_id == user_id).all()
        if not documents:
            return jsonify({"error": "No se encontraron documentos válidos para el usuario."}), 404

        # Obtener palabras clave del usuario
        keywords = Keyword.query.filter_by(user_id=user_id).all()
        if not keywords:
            return jsonify({"error": "El usuario no tiene palabras clave registradas."}), 404

        keyword_list = [keyword.keyword for keyword in keywords]

        # Crear una nueva búsqueda en la tabla Search
        nueva_busqueda = Search(
            name=nombre_busqueda,
            user_id=user_id,
            # created_at=datetime.utcnow() se crea solo creo
        )
        db.session.add(nueva_busqueda)
        db.session.flush()  # Obtener el ID de la búsqueda antes de confirmar

        # Buscar palabras clave
        for document in documents:

            doc = fitz.open(document.file_path)

            for page in doc:
                for keyword in keyword_list:
                    text_instances = page.search_for(keyword)

                    for inst in text_instances:
                        # Resaltar el texto encontrado
                        page.add_highlight_annot(inst)
                        # Crear un nuevo resultado en la tabla SearchResult
                        search_result = SearchResult(
                        search_id=nueva_busqueda.id,
                        document_id=document.id,
                        keyword=keyword
                        )
                        db.session.add(search_result) 

        # Confirmar la transacción
        db.session.commit()

        # Guardar el PDF resaltado en memoria
        output_stream = io.BytesIO()
        doc.save(output_stream, garbage=4, deflate=True)
        doc.close()

        # Enviar el archivo PDF modificado como respuesta
        output_stream.seek(0)
        return send_file(
            output_stream,
            as_attachment=True,
            download_name=f"{document.filename}_highlighted.pdf",
            mimetype="application/pdf"
        )
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Error al realizar la búsqueda.", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Error al procesar el PDF", "details": str(e)}), 500


# AGREGAR COMENTARIO A LA BUSQUEDA #
@app.route("/busqueda/<int:search_id>/comentario", methods=["PUT"])
@jwt_required()
def agregar_comentario_busqueda(search_id):
    try:
        # Obtener ID del usuario autenticado
        user_id = get_jwt_identity()
        data = request.json
        comentario = data.get("comentario")

        # Validación
        if not comentario:
            return jsonify({"error": "El comentario no puede estar vacío."}), 400

        # Verificar si la búsqueda pertenece al usuario
        search = Search.query.filter_by(id=search_id, user_id=user_id).first()
        if not search:
            return jsonify({"error": "Búsqueda no encontrada o no pertenece al usuario."}), 404

        # Actualizar el comentario de la búsqueda
        search.comment = comentario
        db.session.commit()

        return jsonify({"message": "Comentario agregado con éxito."}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Error al agregar el comentario.", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Ocurrió un error inesperado.", "details": str(e)}), 500


# GET, PATCH Y DELETE DE EJEMPLOS #

@app.route("/usuarios", methods=["GET"])
def get_usuarios():
    users = User.query.all()
    json_users = list(map(lambda x: x.to_json(), users))
    return jsonify({"usuarios": json_users}) #Aca manda codigo 200 por default


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


# PARA QUE FUNCIONE LA APLICACION #

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        jwt = JWTManager(app)

    app.run(debug=True)