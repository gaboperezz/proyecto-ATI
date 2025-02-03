from urllib.parse import urlparse
import camelot # type: ignore
from flask import render_template, request, jsonify, send_file
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import pandas as pd
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
import requests
from bs4 import BeautifulSoup
import webbrowser

# RUTAS DE INTERES #

@app.route('/')
def index():
    return render_template('index.html')


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
    user_id = get_jwt_identity()

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
                    align=0  # Alinear el texto a la izquierda
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
@app.route("/getBusquedas", methods=["GET"])
@jwt_required()
def get_busquedas():
    try:
        usuario_id = get_jwt_identity()
        busquedas = Search.query.filter_by(user_id=usuario_id).all()

        if(busquedas):
            # Formatear los resultados en JSON
            resultado = [
                {
                    "id": busqueda.id,
                    "nombre": busqueda.name,
                    "comentario": busqueda.comment,
                    "fechaRealizacion": busqueda.search_date
                    #.strftime("%Y-%m-%d %H:%M:%S")
                }
                for busqueda in busquedas
            ]
            return jsonify({"busquedas": resultado}), 200
        else:
            return jsonify({"message":"No se encontraron búsquedas para este usuario"}), 404

    except Exception as e:
        return jsonify({"error": "Error al obtener búsquedas", "details": str(e)}), 500


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
@app.route("/busqueda/<int:search_id>/comentario", methods=["PATCH"])
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
    

# EMPIEZA EL SCRAPPING #

# Función para crear carpetas

def crear_carpeta(nombre_carpeta):
    if not os.path.exists(nombre_carpeta):
        os.makedirs(nombre_carpeta)

def guardar_archivo(pdf_bytes):
    """Guarda el PDF en el sistema de archivos y retorna la ruta"""
    nombre_archivo = f"{uuid.uuid4()}.pdf"  # Nombre único
    ruta_completa = os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo)
    
    with open(ruta_completa, "wb") as f:
        f.write(pdf_bytes)

    return ruta_completa
import uuid

def descargar_y_abrir_pdf(articulo_url, carpeta, is_revurugcardiol=False):
    try:
        # Obtener el contenido de la página del artículo
        respuesta = requests.get(articulo_url)
        respuesta.raise_for_status()
        soup = BeautifulSoup(respuesta.text, "html.parser")

        # Si es la revista revurugcardiol.org.uy, buscar dentro del div con clase 'seccion-pdf'
        if is_revurugcardiol:
            pdf_div = soup.find("div", class_="seccion-pdf")
            if pdf_div:
                pdf_link = pdf_div.find("a", href=True)
                if pdf_link and "href" in pdf_link.attrs:
                    pdf_url = requests.compat.urljoin(articulo_url, pdf_link["href"])
                    # Abrir el PDF en el navegador
                    # webbrowser.open(pdf_url)

        else:
            # Buscar el enlace al visor de PDF (con clase específica) para otras revistas
            pdf_viewer_link = soup.find("a", {"class": "obj_galley_link pdf"})
            if pdf_viewer_link:
                pdf_url = requests.compat.urljoin(articulo_url, pdf_viewer_link["href"])
                print(f"Pdf viewer link: {pdf_url}")
                # Abrir el PDF en el navegador
                # webbrowser.open(pdf_url)


        print("HOLAAAAAAAAA1")
        if pdf_url:
            print(f"HOLAAAAAAAAA2: {pdf_url}")
            pdf_response = requests.get(pdf_url)
            pdf_response.raise_for_status()
            pdf_bytes = pdf_response.content

            # Extraer dominio del PDF
            url_parseada = urlparse(pdf_url)
            dominio = url_parseada.netloc.replace("www.", "").replace(".", "_")  # revista_rmu_org_uy por ejemplo

            nombre_archivo = pdf_url.split("/")[-1]
            nombre_archivo_actualizado = f"{dominio}_{nombre_archivo}"  # Ejemplo: revista_rmu_org_uy_1081_1048.pdf

            # Guardar en la base de datos
            nuevo_documento = Document(
                user_id=get_jwt_identity(),
                filename=nombre_archivo_actualizado,
                file_path=guardar_archivo(pdf_bytes),  # Guardamos la ruta
                uploaded_at=datetime.now(timezone.utc)
            )
            db.session.add(nuevo_documento)
            db.session.commit()
            
            print(f"PDF guardado en BD: {nuevo_documento.filename}")
            return True
        else:
            print(f"No se encontró un PDF en: {articulo_url}")
            return False
    except Exception as e:
        print(f"Error al procesare articulo:  {articulo_url}: {e}")


def ultima_revista(url_base):
    try:
        respuesta = requests.get(url_base)
        respuesta.raise_for_status()
        soup = BeautifulSoup(respuesta.text, "html.parser")

        if "revurugcardiol.org.uy" in url_base:
            # Buscar el enlace contenedor de la revista más reciente
            ultimo_link_encontrado = soup.find("a", {"class": "link-numero"})
            if ultimo_link_encontrado and "href" in ultimo_link_encontrado.attrs:
                url_entera = requests.compat.urljoin(url_base, ultimo_link_encontrado["href"])
                print(f"Última URL encontrada: {url_entera}")
                return url_entera
            else:
                print("No se encontró el enlace de la revista más reciente. (REVURUGCARDIOL)")
                return None
        elif "spu.org.uy" in url_base:
            # Encontrar el título "Revistas 2024"
            revistas_2024_div = soup.find("a", {"title": "Revistas 2024"})
            if not revistas_2024_div:
                print("No se encontró el enlace a 'Revistas 2024'.")
            else:
                # Buscar todos los enlaces después de "Revistas 2024"
                parent_div = revistas_2024_div.find_parent("div")
                siguientes_enlaces = parent_div.find_all_next("a", {"title": True})
                
                if siguientes_enlaces:
                    # Seleccionar el primer enlace válido (el más reciente)
                    ultimo_enlace_url = siguientes_enlaces[1]["href"]  # Aquí se elige el primero de la lista
                    url_entera = requests.compat.urljoin(url_base, ultimo_enlace_url)  # Resolver URL completa
                    print(f"Último número encontrado: {siguientes_enlaces[1]['title']} -> {url_entera}")
                    return url_entera  # Retorna el enlace completo
                else:
                    print("No se encontraron números después de 'Revistas 2024'.")
        elif "ago.uy" in url_base:
              # Buscar el enlace al "Último número" en el div con clase 'ctas'
            ultimo_div = soup.find("div", class_="ctas")
            if ultimo_div:
                link = ultimo_div.find("a", href=True)
                if link:
                    url_entera = requests.compat.urljoin(url_base, link["href"])
                    print(f"Último número encontrado (AGO): {url_entera}")
                    return url_entera
            print(f"No se encontró el enlace al último número en {url_base}")
            return None
        elif "www.boletinfarmacologia.hc.edu.uy" in url_base: 
            print("ENTRÉ")
            # Buscar la sección que contiene los enlaces a los boletines
            seccion_boletines = soup.find("section", id="sp-main-body")
            if seccion_boletines:
                # Buscar todos los artículos de boletines (que contienen los años)
                boletines_links = seccion_boletines.find_all("a", href=True)
                
                # Filtrar los enlaces que corresponden a boletines con años, como "/boletines/bolet/2024"
                boletines_anios = [
                    requests.compat.urljoin(url_base, link["href"])
                    for link in boletines_links if "/boletines/bolet/" in link["href"]
                ]
                
                # Obtener el enlace al boletín más reciente (suponiendo que el último enlace es el más reciente)
                if boletines_anios:
                    ultimo_enlace_url = boletines_anios[0]  # El más reciente debe ser el primero en la lista
                    print(f"Último boletín encontrado: {ultimo_enlace_url}")
                    return ultimo_enlace_url
                else:
                    print("No se encontraron boletines disponibles.")
            else:
                print("No se encontró la sección de boletines.")
        elif "casmu.com.uy" in url_base:
            print("Procesando CasmuCerca...")
            # Buscar la sección de ediciones anteriores
            secion_ediciones = soup.find("span", text="Ediciones anteriores Revista CasmuCerca")
            if secion_ediciones:
                # Buscar el 'dl' que contiene las ediciones de 2024
                dl = secion_ediciones.find_next("dl", class_="sc-accordions")
                if dl:
                    # Buscar el primer enlace dentro de 2024
                    seccion_2024 = dl.find("dt", text="2024")
                    if seccion_2024:
                        # Obtener los enlaces de las revistas dentro de 2024
                        links_2024 = seccion_2024.find_next("dd").find_all("a", href=True)
                        if links_2024:
                            # Tomar el primer enlace, el más reciente
                            ultimo_enlace_url = links_2024[0]["href"]
                            url_entera = requests.compat.urljoin(url_base, ultimo_enlace_url)
                            print(f"Última revista encontrada: {url_entera}")
                            return url_entera
                        else:
                            print("No se encontraron enlaces dentro de 2024.")
                    else:
                        print("No se encontró la sección para el año 2024.")
                else:
                    print("No se encontró la sección de 'Ediciones anteriores'.")
            else:
                print("No se encontró el texto 'Ediciones anteriores Revista CasmuCerca'.")
        elif "opcionmedica.com.uy" in url_base:
            # Lógica para opcionmedica.com.uy
            try:
                # Buscar el primer artículo que contiene la clase `elementor-post`
                article = soup.find("article", class_="elementor-post")
                if article:
                    # Extraer el primer enlace dentro del artículo
                    link = article.find("a", href=True)
                    if link:
                        url_entera = requests.compat.urljoin(url_base, link["href"])
                        print(f"Última revista encontrada (Opción Médica): {url_entera}")
                        return url_entera
                    else:
                        print("No se encontró un enlace en el artículo correspondiente.")
                else:
                    print("No se encontró el artículo correspondiente a la última revista.")
            except Exception as e:
                print(f"Error al procesar opcionmedica.com.uy: {e}")
        else:
            # Selector genérico para otras páginas
            ultimo_link_encontrado = soup.find("a", {"class": "title"})
            if ultimo_link_encontrado:
                url_entera = requests.compat.urljoin(url_base, ultimo_link_encontrado["href"])
                print(f"Latest issue URL: {url_entera}")
                return url_entera
            else:
                print("No se encontró el enlace de la revista más reciente.")
                return None
    except Exception as e:
        print(f"Error finding the latest magazine: {e}")
        return None


def sacar_articulos_de_revista(issue_url):
    try:
        respuesta = requests.get(issue_url)
        respuesta.raise_for_status()
        soup = BeautifulSoup(respuesta.text, "html.parser")

        # Encontrar enlaces de los artículos (caso genérico y específico)
        if "revurugcardiol.org.uy" in issue_url:
            links_articulos = soup.find_all("a", href=True)
            articles = [
                requests.compat.urljoin(issue_url, link["href"])
                for link in links_articulos if "/index.php/articulo/" in link["href"]
            ]
        elif "spu.org.uy" in issue_url:
            print("Procesando artículos para SPU...")
            links_articulos = soup.find_all("a", href=True)
            # Depuración: Mostrar los enlaces encontrados
            for link in links_articulos:
                print(f"Enlace encontrado: {link['href']}")

            # Filtrar enlaces que terminen en .pdf
            articles = [
                requests.compat.urljoin(issue_url, link["href"])
                for link in links_articulos if link["href"].lower().endswith(".pdf")
                
            ]
        elif "ago.uy" in issue_url:
            print("Procesando artículos para AGO...")
            # Buscar el div con clase 'panel has-blocks'
            panel_div = soup.find("div", class_="panel has-blocks")
            if panel_div:
                # Buscar el enlace dentro del div
                pdf_link = panel_div.find("a", href=True, class_="panel-block")
                if pdf_link:
                    pdf_url = requests.compat.urljoin(issue_url, pdf_link["href"])
                    print(f"Enlace al PDF completo encontrado: {pdf_url}")
                    articles = [pdf_url]
                else:
                    print("No se encontró el enlace al PDF dentro del 'panel has-blocks'.")
            else:
                print("No se encontró el div 'panel has-blocks' para AGO.")
        elif "farmacologia.hc.edu.uy" in issue_url:
            print("Procesando artículos para Farmacología...")

            # Buscar todos los <span> que contienen información de volumen
            span_volumen = soup.find_all('span', string=re.compile(r'Volumen \d+, Número \d+ / \w+ \d{4}'))

            if span_volumen:
                # Seleccionar el último volumen (más reciente)
                ultimo_volumen = span_volumen[-1]
                
                # Encontrar los párrafos que siguen a este último volumen
                p_tags = ultimo_volumen.find_parent().find_all_next('p')
                
                articles = []
                for p in p_tags:
                    a_tags = p.find_all('a', href=True)  # Buscar todos los enlaces dentro de cada párrafo
                    for a in a_tags:
                        articles.append(requests.compat.urljoin(issue_url, a['href']))
            else:
                print("No se encontró un volumen válido.")
                articles = []
        elif "casmu.com.uy" in issue_url:

            # Buscar todos los enlaces y filtrar los que contienen "Ver o descargar"
            boton_descargar = soup.find("a", href=True, string=lambda text: text and "Ver o descargar" in text)

            if boton_descargar:
                pdf_url = requests.compat.urljoin(issue_url, boton_descargar["href"])
                print(f"Enlace al PDF completo encontrado: {pdf_url}")
                articles = [pdf_url]
            else:
                print("No se encontró el enlace al PDF para la revista.")
                articles = []    
        elif "opcionmedica.com.uy" in issue_url:
            print("Procesando artículos para Opción Médica...")

            # Buscar el script que contiene la URL del PDF
            matchScript = re.search(r'var option_df_\d+ = \{[^}]*"source":\s*"([^"]+\.pdf)"', respuesta.text)

            if matchScript:
                pdf_url = matchScript.group(1)  # Extraer la URL del PDF
                
                # Corregir la URL, reemplazando secuencias escapadas
                pdf_url = pdf_url.replace("\\/", "/")  # Reemplaza \\/ por /
                pdf_url = pdf_url.replace("\\", "")  # Elimina las barras invertidas extra

                print(f"Enlace al PDF encontrado: {pdf_url}")
                articles = [pdf_url]  # Devolver la URL en una lista
            else:
                print("No se encontró ninguna URL de PDF en el código fuente.")
                articles = []
        else:
            links_articulos = soup.find_all("a", href=True)           
            articles = [
                requests.compat.urljoin(issue_url, link["href"])
                for link in links_articulos if "/article/view/" in link["href"]
            ]

        print(f"Se han encontrado: {len(articles)} articulos.")
        return articles
    except Exception as e:
        print(f"No se encontraron articulos: {e}")
        return []

def descargar():
    # Ruta al archivo con los links
    file_path = os.path.expanduser("backend/txtLinks/link1RevistaAPIs.txt")
    

    with open(file_path, "r") as file:
        lines = file.readlines()

    # Crear carpeta de destino para los PDFs
    crear_carpeta("PDFs")

    total_pdfs = 0

    # Procesar el archivo de texto
    for line in lines:
        line = line.strip().split("-->")[0].strip()  # Limpiar URL
        # Eliminar cualquier prefijo como "3)" antes de la URL
        line = line.split(" ")[-1]  # Tomar solo la última parte de la línea (que debe ser la URL)

        # Verificar si la línea contiene una URL válida
        if line.startswith("http"):
            if "revista.rmu.org.uy" in line:
                # Obtener artículos desde la última revista
                print("Procesando Revista RMU...")
                ultimo_link_revista = ultima_revista(line)
                if ultimo_link_revista:
                    links_articulos = sacar_articulos_de_revista(ultimo_link_revista)
                    for link_articulo in links_articulos:
                        total_pdfs = total_pdfs + 1
                        descargar_y_abrir_pdf(link_articulo, "PDFs")
            elif "revurugcardiol.org.uy" in line:
                # Procesar Revista Uruguaya de Cardiología
                print("Procesando Revista Uruguaya de Cardiología...")
                """ultimo_link_revista = ultima_revista(line)
                if ultimo_link_revista:
                    links_articulos = sacar_articulos_de_revista(ultimo_link_revista)
                    for link_articulo in links_articulos:
                        descargar_y_abrir_pdf(link_articulo, "PDFs", is_revurugcardiol=True)"""
            elif "spu.org.uy" in line:
                print("Procesando SPU...")
                """ultimo_link_revista = ultima_revista(line)
                if ultimo_link_revista:
                    links_articulos = sacar_articulos_de_revista(ultimo_link_revista)
                    for link_articulo in links_articulos:
                        descargar_y_abrir_pdf(link_articulo, "PDFs")"""
            elif "ago.uy" in line:  # Condicional para esta nueva página
                print("Procesando AGO...")
                """ultimo_link_revista = ultima_revista(line)
                if ultimo_link_revista:
                    links_articulos = sacar_articulos_de_revista(ultimo_link_revista)
                    for link_articulo in links_articulos:
                        descargar_y_abrir_pdf(link_articulo, "PDFs")"""
            elif "www.boletinfarmacologia.hc.edu.uy" in line: #LEVANTA TODOS LOS PDF MENOS 2 porque son una pagina y un png,                                                  
                print("Procesando Boletin Farmacologia")
                """ultimo_link_revista = ultima_revista(line)
                if ultimo_link_revista:
                    links_articulos = sacar_articulos_de_revista(ultimo_link_revista)
                    for link_articulo in links_articulos:
                        descargar_y_abrir_pdf(link_articulo, "PDFs")"""
            elif "casmu.com.uy" in line:
                # Halla el pdf que necesitamos ya que dice si o si "Ver o descargar, y luego el numero de revista" (no encontré otra forma)
                # Está en el if de sacar_articulos_de_revista
                print("Procesando Revista CasmuCerca...")
                """ultimo_link_revista = ultima_revista(line)
                if ultimo_link_revista:
                    links_articulos = sacar_articulos_de_revista(ultimo_link_revista)
                    for link_articulo in links_articulos:
                        descargar_y_abrir_pdf(link_articulo, "PDFs")"""
            elif "www.opcionmedica.com.uy" in line: 
                # ESTUVO ULTRA DIFICIL 
                print("Procesando Opcion Medica")
                """ultimo_link_revista = ultima_revista(line)
                if ultimo_link_revista:
                    links_articulos = sacar_articulos_de_revista(ultimo_link_revista)
                    for link_articulo in links_articulos:
                        descargar_y_abrir_pdf(link_articulo, "PDFs")"""
            else:
                # Para otras revistas
                print("Procesando otras revistas...")
                """links_articulos = sacar_articulos_de_revista(line)
                for link_articulo in links_articulos:
                    descargar_y_abrir_pdf(link_articulo, "PDFs")"""
        else:
            print(f"URL inválida: {line}")
        print(total_pdfs)
    return total_pdfs / 2


# Endpoint para triggerear el scraping
@app.route('/scraping/revistas', methods=['GET'])
@jwt_required()
def obtener_revistas():
    try:
        # Ejecutar scraping
        total_pdfs = descargar()
        print(f"Pdfs: {total_pdfs}")
        
        # Listar PDFs descargados
        pdfs = os.listdir("PDFs") if os.path.exists("PDFs") else []
        
        return jsonify({
            "message": f"Scraping completado. {total_pdfs} PDFs descargados",
            "revistas": total_pdfs
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Error en el scraping",
            "details": str(e)
        }), 500
                # TERMINA EL SCRAPING #
                
# TERMINA EL SCRAPING #

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

if __name__ == "__app__":
    with app.app_context():
        db.create_all()
        jwt = JWTManager(app)

    app.run(host='0.0.0.0', port=8000,debug=True)