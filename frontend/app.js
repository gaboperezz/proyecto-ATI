const API_URL = "http://127.0.0.1:5000/"; //PONER URL DE LA API

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

    const response = await fetch(`${API_URL}/crear_usuario`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
    });

    const resultado = await response.json();
    alert(resultado.message || resultado.error);
});

/* LOGIN Y LOGOUT */

document.getElementById("btnLogin").addEventListener("click", async () => {
    const username = document.getElementById("txtLoginUsuario").value;
    const password = document.getElementById("txtLoginPassword").value;

    const response = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
    });

    if (response.ok) {
        const resultado = await response.json();
        // token = resultado.token;
        localStorage.setItem("token", resultado.token);
        localStorage.setItem("idLogueado", resultado.idUsuario);
        document.getElementById("divLogin").style.display = "none";
        document.getElementById("divMenuPrincipal").style.display = "block";
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
    alert("Sesion cerrada.")
});



/* PROTECTED DE EJEMPLO (pide autorizacion en el header) */ 

document.getElementById("btnProtected").addEventListener("click", async () =>{
    const response = await fetch(`${API_URL}/protected`, {
        method: "GET",
        headers: { 
            "Authorization": `Bearer ${localStorage.getItem("token")}`,
            "Content-Type": "application/json"
        },
    });

    const resultado = await response.json();
    alert(resultado.message || resultado.error);
})

/* ADJUNTAR ARCHIVO PDF */

/* OBTENER PALABRAS CLAVE */
document.getElementById("btnGetPalabrasClave").addEventListener("click", async () => {
    const response = await fetch(`${API_URL}/getPalabrasClave/${localStorage.getItem("idLogueado")}`, {
        method: "GET",
        headers: {
            "Authorization": `Bearer ${localStorage.getItem("token")}`,
            "Content-Type": "application/json"
        },
    });

    const resultado = await response.json();
    alert(resultado.message || resultado.error)
    console.log(resultado)
})

/* AGREGAR PALABRAS CLAVE */

/* ELIMINAR PALABRAS CLAVE */

/* VER BUSQUEDAS ANTERIORES */

/* REALIZAR BUSQUEDA */



/* EJEMPLOS */

document.getElementById("task-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const content = document.getElementById("task-input").value;

    const response = await fetch(`${API_URL}/tasks`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content }),
    });

    if (response.ok) {
        fetchTasks();
        document.getElementById("task-input").value = "";
    }
});

async function fetchTasks() {
    const response = await fetch(`${API_URL}/tasks`, {
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
    await fetch(`${API_URL}/tasks/${taskId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
    });
    fetchTasks();
}
