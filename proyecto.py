import customtkinter
from tkinter import filedialog
from pdfminer.high_level import extract_pages, extract_text

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")

root = customtkinter.CTk()
root.geometry("500x350")

def login():
    print("HOLA")

def openFile():
    filepath = filedialog.askopenfilename()
    archivo = open(filepath, 'rb')
    text = extract_text(archivo)
    print(text)


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

checkBox = customtkinter.CTkCheckBox(master=frame, text="Remember Me")
checkBox.pack(pady=12, padx=10)

button2 = customtkinter.CTkButton(master=frame, text="Adjuntar archivo",command=openFile)
button2.pack(pady=15, padx=12)

root.mainloop()