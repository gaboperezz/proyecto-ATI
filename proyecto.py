import customtkinter
from tkinter import filedialog
from pdfminer.high_level import extract_pages, extract_text

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")

root = customtkinter.CTk()
root.geometry("500x350")

#Datos para simular la base de datos#
class Usuario:
    def __init__(self, nombre, contrasena):
        self.nombre = nombre
        self.contrasena = contrasena
    
usuario1 = Usuario("chinac", "elchelo")
usuario2 = Usuario("zgabo4", "lostussienvelez")

usuarios = {usuario1, usuario2}

 
def login():
    for u in usuarios:
        if(entry1.get() == u.nombre and entry2.get() == u.contrasena): 
            print("SI")
            break
    else: print("NO")

def openFile():
    filepath = filedialog.askopenfilename()
    print(filepath)
    archivo = open(filepath, 'rb')
    text = extract_text(archivo)
    print(text)


def registrarse():
    frame.pack_forget()
    frameRegistro.pack(pady=20, padx=60, fill="both", expand=True)

def confirmarRegistro():
    print("HOLA")


    
# FRAME LOGIN #
frame = customtkinter.CTkFrame(master=root)
frame.pack(pady=20, padx=60, fill="both", expand=True)

label = customtkinter.CTkLabel(master=frame, text="Login")
label.pack(pady=12, padx=10)

entry1 = customtkinter.CTkEntry(master=frame, placeholder_text="Username")
entry1.pack(pady=12, padx=10)

entry2 = customtkinter.CTkEntry(master=frame, placeholder_text="Password", show="*")
entry2.pack(pady=12, padx=10)

button = customtkinter.CTkButton(master=frame, text="Login", command=login)
button.pack(pady=12, padx=10)

button = customtkinter.CTkButton(master=frame, text="No tengo cuenta", command=registrarse)
button.pack(pady=12, padx=135)

checkBox = customtkinter.CTkCheckBox(master=frame, text="Remember Me")
checkBox.pack(pady=12, padx=10)

button2 = customtkinter.CTkButton(master=frame, text="Adjuntar archivo",command=openFile)
button2.pack(pady=15, padx=12)

# FRAME REGISTRO #
frameRegistro = customtkinter.CTkFrame(master=root)

labelRegistro = customtkinter.CTkLabel(master=frameRegistro, text="Registrarse")
labelRegistro.pack(pady=12, padx=10)

entry1Registro = customtkinter.CTkEntry(master=frameRegistro, placeholder_text="Username")
entry1Registro.pack(pady=12, padx=10)

entry2Registro = customtkinter.CTkEntry(master=frameRegistro, placeholder_text="Password", show="*")
entry2Registro.pack(pady=12, padx=10)

buttonRegistro = customtkinter.CTkButton(master=frameRegistro, text="Confirmar", command=confirmarRegistro)
buttonRegistro.pack(pady=12, padx=10)


root.mainloop()