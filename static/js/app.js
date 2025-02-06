const API_URL = "https://proyecto-perezulivi-b8atf7eqguhph3a4.canadacentral-01.azurewebsites.net/"
// "http://127.0.0.1:8000"; //PONER URL DE LA API
// "https://proyecto-perezulivi-b8atf7eqguhph3a4.canadacentral-01.azurewebsites.net"


/* IR A LOGIN O REGISTRO */
document.getElementById("btnIrARegistro").addEventListener("click", () =>{
    document.getElementById("divLogin").style.display = "none";
    document.getElementById("divRegistrar").style.display = "block";
})

document.getElementById("btnIrALogin").addEventListener("click", () =>{
    document.getElementById("divRegistrar").style.display = "none";
    document.getElementById("divLogin").style.display = "block";
})


/* REGISTRO */
document.getElementById("btnRegistro").addEventListener("click", async () => {
    const username = document.getElementById("txtRegistroUsuario").value;
    const password = document.getElementById("txtRegistroPassword").value;

    const response = await fetch(`${API_URL}crear_usuario`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
    });

    const resultado = await response.json();
    alert(resultado.message || resultado.error);

    // Aca hay que validar errores cuando se trata de un usuario repetido
});


/* LOGIN Y LOGOUT */
document.getElementById("btnLogin").addEventListener("click", async () => {
    const username = document.getElementById("txtLoginUsuario").value;
    const password = document.getElementById("txtLoginPassword").value;

    const response = await fetch(`${API_URL}login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
    });

    if (response.ok) {
        const resultado = await response.json();
        // token = resultado.token;
        localStorage.setItem("token", resultado.token);
        localStorage.setItem("idLogueado", resultado.idUsuario);
        cargarDocumentos();
        cargarDocumentos2();
        // cargarPalabrasClave();
        document.getElementById("divLogin").style.display = "none";
        document.getElementById("divMenuPrincipal").style.display = "block";
        document.getElementById("txtLoginUsuario").value = "";
        document.getElementById("txtLoginPassword").value = "";

        document.getElementById("botonesMenu").style.display = "block";
        // document.getElementById("task-form").style.display = "block";
        // fetchTasks();
    } else {
        alert("Credenciales inválidas.");
    }
});

document.getElementById("btnLogout").addEventListener("click", async () => {

    localStorage.removeItem("token");
    document.getElementById("divLogin").style.display = "block";
    document.getElementById("divMenuPrincipal").style.display = "none";
    document.getElementById("divRegistrar").style.display = "none";

    document.getElementById("botonesMenu").style.display = "none";

    alert("Sesion cerrada.")
});


/* LOGICA DEL OJO CONTRASEÑA */
document.getElementById("togglePasswordLogin").addEventListener("click", () => {
    const passwordInput = document.getElementById("txtLoginPassword");
    const togglePasswordIcon = document.getElementById("togglePasswordLogin");

    // Alternar el tipo del campo entre 'password' y 'text'
    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        togglePasswordIcon.src = "static/img/ojo-abierto.png"; // Cambiar a ícono de ojo cerrado
    } else {
        passwordInput.type = "password";
        togglePasswordIcon.src = "static/img/ojo-cerrado.png"; // Cambiar a ícono de ojo abierto
    }
});

document.getElementById("togglePasswordRegistro").addEventListener("click", () => {
    const passwordInput = document.getElementById("txtRegistroPassword");
    const togglePasswordIcon = document.getElementById("togglePasswordRegistro");

    // Alternar el tipo del campo entre 'password' y 'text'
    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        togglePasswordIcon.src = "static/img/ojo-abierto.png"; // Cambiar a ícono de ojo cerrado
    } else {
        passwordInput.type = "password";
        togglePasswordIcon.src = "static/img/ojo-cerrado.png"; // Cambiar a ícono de ojo abierto
    }
});

/* SUBIR ARCHIVO PDF */

document.getElementById("form-PDF").addEventListener("submit", async (event) => {
    event.preventDefault(); // Previene el envío del formulario por defecto

    const archivo = document.getElementById("pdfFile").files[0];
    if (!archivo) {
        alert("Por favor, selecciona un archivo PDF.");
        return;
    }

    const formData = new FormData();
    formData.append("file", archivo);

    try {
        const response = await fetch(`${API_URL}upload/pdf`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            alert(`PDF subido con éxito: ${result.filename}`);
        } 
        else {
            alert(`Error: ${result.error}`);
        }
    } catch (error) {
        console.error("Error al subir el archivo PDF:", error);
        alert("Ocurrió un error al intentar subir el archivo.");
    }
});

// Lógica para el botón de scraping
document.getElementById("btnScraping").addEventListener("click", async () => {
    try {
        const response = await fetch(`${API_URL}scraping/revistas`, {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            // Mostrar solo la cantidad de PDFs obtenidos
            const cantidadPDFs = data.revistas; // La clave "revistas" ahora es un array
            document.getElementById("cantidadRevistas").textContent = cantidadPDFs;
        } else {
            alert("Error al obtener revistas: " + data.error);
            console.error(data.details);
        }
    } catch (error) {
        console.error("Error al realizar el scraping:", error);
        alert("Ocurrió un error al realizar el scraping.");
    }
});


/* TRADUCIR PDF */
document.getElementById("form-traducirPDF").addEventListener("submit", async (event) => {
    event.preventDefault(); // Prevenir el envío por defecto del formulario

    // Obtener los documentos seleccionados
    const documentosSeleccionados = Array.from(document.querySelectorAll("#listaDocumentos2 input:checked"))
    .map(checkbox => checkbox.value);

   // print(documentosSeleccionados)

    if (documentosSeleccionados.length === 0) {
        alert("Por favor, selecciona al menos un archivo PDF para traducir.");
        return;
    }

    try {
        // Enviar solicitud al backend
        const response = await fetch(`${API_URL}translate/pdf`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                idsDocumentos2: documentosSeleccionados, // IDs de los documentos seleccionados
            }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            alert(`Error: ${errorData.error}`);
            console.error(errorData.details);
            return;
        }

        // Recibir el PDF traducido
        const blob = await response.blob();

        // Crear una URL temporal para el PDF traducido
        const pdfUrl = URL.createObjectURL(blob);

        // Abrir el PDF en una nueva pestaña
        window.open(pdfUrl, "_blank");

        // Liberar la URL creada después de abrirla
        URL.revokeObjectURL(pdfUrl);
    } catch (error) {
        console.error("Error al traducir el PDF:", error);
        alert("Ocurrió un error al intentar traducir el archivo.");
    }
});


/* AGREGAR PALABRA CLAVE */

document.getElementById("btnAgregarPalabraClave").addEventListener("click", async () => {
    const word = document.getElementById("txtPalabraClave").value;

    const response = await fetch(`${API_URL}crearPalabraClave`, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${localStorage.getItem("token")}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ word })
    });

    if (response.ok) {
        alert(resultado.message)
    } else{
        alert(resultado.error || resultado.message);
    }
})

/* SUBIR ARCHIVO DE PALABRAS CLAVE */

document.getElementById("form-txt").addEventListener("submit", async (event) => {
    event.preventDefault(); // Previene el envío del formulario por defecto

    const archivo = document.getElementById("txtFile").files[0];
    if (!archivo) {
        alert("Por favor, selecciona un archivo .txt.");
        return;
    }

    const formData = new FormData();
    formData.append("file", archivo);

    try {
        const response = await fetch(`${API_URL}upload/txt`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: formData
        });

        const result = await response.json();
        if (response.ok) {
            alert(`Palabras clave subidas con éxito.`);
            console.log(result.keywords.join(", "));
        } else {
            alert(`Error: ${result.error}`);
        }
    } catch (error) {
        console.error("Error al subir el archivo .txt:", error);
        alert("Ocurrió un error al intentar subir el archivo.");
    }
});

// CARGAR LISTA DE PALABRAS CLAVE
document.getElementById("btnListadoPalabrasClave").addEventListener("click", cargarPalabrasClave)

async function cargarPalabrasClave() {
    document.getElementById("btnOcultarListadoPalabrasClave").style.display = "block";
    document.getElementById("divListaPalabrasClave").style.display = "block";

    const response = await fetch(`${API_URL}getPalabrasClave`, {
        method: "GET",
        headers: {
            "Authorization": `Bearer ${localStorage.getItem("token")}`
        }
    });

    const data = await response.json();
    if (response.ok) {
        const listaPalabrasClave = document.getElementById("divListaPalabrasClave");
        listaPalabrasClave.innerHTML = "";
        i=0;
        data.keywords.forEach(kw => {
            const li = document.createElement("li");
            li.textContent = kw;
            const deleteBtn = document.createElement("button");
            deleteBtn.textContent = "Eliminar";
            // deleteBtn.addEventListener("click", () => eliminarPalabraClave(data.keywordsIds[i]));
            deleteBtn.addEventListener("click", ((id) => () => eliminarPalabraClave(id))(data.keywordsIds[i]));
            console.log(data.keywordsIds[i])
            li.appendChild(deleteBtn);
            listaPalabrasClave.appendChild(li);
            i++;
        });
    } else {
        if(data.message){
            alert(data.message);
        }else{
            alert("Error al cargar palabras clave: " + data.error);
            alert(data.details)
        }
    }
}

/* OCULTAR LISTADO DE PALABRAS CLAVE */

document.getElementById("btnOcultarListadoPalabrasClave").addEventListener("click", () => {
    document.getElementById("btnOcultarListadoPalabrasClave").style.display = "none";
    document.getElementById("divListaPalabrasClave").style.display = "none";
})

/* ELIMINAR PALABRAS CLAVE */

async function eliminarPalabraClave(idPalabraClave){
    const response = await fetch(`${API_URL}eliminarPalabraClave/${idPalabraClave}`, {
        method: "DELETE",
        headers: {
            "Authorization": `Bearer ${localStorage.getItem("token")}`,
            "Content-Type": "application/json"
        }
    });

    const resultado = await response.json();
    if (response.ok) {
        alert(resultado.message)
    } else{
        alert(resultado.error || resultado.message);
    }
    cargarPalabrasClave();
}

/* VER BUSQUEDAS ANTERIORES */

document.getElementById("btnVerBusquedas").addEventListener("click", cargarBusquedas)

async function cargarBusquedas(){
    document.getElementById("btnOcultarBusquedas").style.display = "block";
    document.getElementById("divListadoBusquedasAnteriores").style.display = "block";

    const response = await fetch(`${API_URL}getBusquedas`, {
        method: "GET",
        headers: {
            "Authorization": `Bearer ${localStorage.getItem("token")}`
        }
    });

    const data = await response.json();
    if (response.ok) {
        const listaBusquedas = document.getElementById("divListadoBusquedasAnteriores");
        listaBusquedas.innerHTML = "";
        i=0;
        data.busquedas.forEach(busq => {
            const li = document.createElement("li");
            li.textContent = busq.id + " - " + busq.nombre + " - " + busq.fechaRealizacion + " - " + busq.comentario;
            listaBusquedas.appendChild(li);
            i++;
        });
    } else {
        if(data.message){
            alert(data.message);
        }else{
            alert("Error al cargar palabras clave: " + data.error);
            alert(data.details)
        }
    }
}

/* OCULTAR LISTADO DE PALABRAS CLAVE */

document.getElementById("btnOcultarBusquedas").addEventListener("click", () => {
    document.getElementById("btnOcultarBusquedas").style.display = "none";
    document.getElementById("divListadoBusquedasAnteriores").style.display = "none";
})

// CARGAR DOCUMENTOS PARA BUSQUEDA
// Cargar lista de documentos

async function cargarDocumentos() {
    const response = await fetch(`${API_URL}user/documentos`, {
        method: "GET",
        headers: {
            "Authorization": `Bearer ${localStorage.getItem("token")}`
        }
    });

    const data = await response.json();
    if (response.ok) {
        const listaDocumentos = document.getElementById("listaDocumentos");
        data.documents.forEach(doc => {
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.value = doc.id;
            checkbox.id = `doc-${doc.id}`;

            const label = document.createElement("label");
            label.htmlFor = `doc-${doc.id}`;
            label.textContent = doc.name;

            const br = document.createElement("br");
            listaDocumentos.appendChild(checkbox);
            listaDocumentos.appendChild(label);
            listaDocumentos.appendChild(br);
        });
    } else {
        alert("Error al cargar documentos: " + data.error);
        alert(data.details)
    }
}

async function cargarDocumentos2() {
    const response = await fetch(`${API_URL}user/documentos`, {
        method: "GET",
        headers: {
            "Authorization": `Bearer ${localStorage.getItem("token")}`
        }
    });

    const data = await response.json();
    if (response.ok) {
        const listaDocumentos = document.getElementById("listaDocumentos2");
        data.documents.forEach(doc => {
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.value = doc.id;
            checkbox.id = `doc-${doc.id}`;

            const label = document.createElement("label");
            label.htmlFor = `doc-${doc.id}`;
            label.textContent = doc.name;

            const br = document.createElement("br");
            listaDocumentos.appendChild(checkbox);
            listaDocumentos.appendChild(label);
            listaDocumentos.appendChild(br);
        });
    } else {
        alert("Error al cargar documentos: " + data.error);
        alert(data.details)
    }
}


// REALIZA BUSQUEDA Y DEVUELVE PDF CON HIGHLIGHT
document.getElementById("form-busqueda").addEventListener("submit", async (event) => {
    event.preventDefault();

    const documentosSeleccionados = Array.from(document.querySelectorAll("#listaDocumentos input:checked"))
    .map(checkbox => checkbox.value);

    if (documentosSeleccionados.length === 0) {
        alert("Por favor, selecciona al menos un archivo PDF.");
        return;
    }

    const nombreBusqueda = document.getElementById("nombreBusqueda").value;

    try {
        const response = await fetch(`${API_URL}busqueda`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                idsDocumentos: documentosSeleccionados,
                nombreBusqueda: nombreBusqueda
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            alert(`Error: ${errorData.error}`);
            alert(errorData.details)
            return;
        }

        // Obtén el archivo PDF de la respuesta
        const blob = await response.blob();

        // Crea una URL temporal para el PDF
        const pdfUrl = URL.createObjectURL(blob);

        // Abre el PDF en una nueva pestaña
        window.open(pdfUrl, "_blank");

        // // Opcion para que se descargue
        // const link = document.createElement("a");
        // link.href = pdfUrl;
        // link.download = "resultado_busqueda.pdf"; // Nombre del archivo descargado
        // link.click();

    } catch (error) {
        console.error("Error al resaltar y mostrar el PDF:", error);
        alert("Error al procesar el archivo.");
    }
    URL.revokeObjectURL(pdfUrl);
})

/* AGREGAR COMENTARIO A LA BÚSQUEDA */
document.getElementById("agregarComentario").addEventListener("submit", async (event) =>{
    try {
        event.preventDefault();
        
        const busquedaId = document.getElementById("searchId").value;
        const comentario = document.getElementById("nuevoComentario").value;

        const response = await fetch(`${API_URL}busqueda/${busquedaId}/comentario`, {
            method: "PATCH",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ comentario: comentario }),
        });

        const data = await response.json();

        if (response.ok) {
            alert("Comentario agregado con éxito.");
            cargarBusquedas(); // Actualiza la lista de búsquedas
        } else {
            alert("Error al agregar comentario: " + data.error);
        }
    } catch (error) {
        alert("Error al agregar comentario." + data.error);
    }
})

/* EJEMPLOS */

async function fetchTasks() {
    const response = await fetch(`${API_URL}tasks`, {
        headers: { Authorization: `Bearer ${token}` },
    });

    const tasks = await response.json();
    const taskList = document.getElementById("task-list");
    taskList.innerHTML = "";
    tasks.forEach((task) => {
        const li = document.createElement("li");
        li.textContent = task.content;
        const deleteBtn = document.createElement("button");
        deleteBtn.textContent = "Eliminar";
        deleteBtn.addEventListener("click", () => deleteTask(task.id));
        li.appendChild(deleteBtn);
        taskList.appendChild(li);
    });
}

async function deleteTask(taskId) {
    await fetch(`${API_URL}tasks/${taskId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
    });
    fetchTasks();
}
