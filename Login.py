
import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
import subprocess
import sys
import os

# ============================================================
# CONFIGURACIÓN VISUAL
# ============================================================

COLOR_FONDO = "#F4F7FB"
COLOR_AZUL_OSCURO = "#1F4E78"
COLOR_AZUL = "#2F75B5"
COLOR_AZUL_CLARO = "#DCEAF7"
COLOR_BLANCO = "#FFFFFF"
COLOR_TEXTO = "#263238"
COLOR_GRIS = "#607D8B"


# ============================================================
# CONEXIÓN A LA BASE DE DATOS
# ============================================================

def conectar_bd():
    try:
        conexion = mysql.connector.connect(
            host="localhost",
            port=3307,
            user="root",
            password="",
            database="gestion_llantas"
        )
        return conexion

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Error de conexión",
            f"No fue posible conectar con la base de datos.\n\n{error}"
        )
        return None


# ============================================================
# INICIAR SESIÓN
# ============================================================

def iniciar_sesion():
    usuario = entrada_usuario.get().strip()
    contrasena = entrada_contrasena.get()

    if usuario == "":
        messagebox.showwarning(
            "Dato requerido",
            "Ingrese su nombre de usuario."
        )
        entrada_usuario.focus()
        return

    if contrasena == "":
        messagebox.showwarning(
            "Dato requerido",
            "Ingrese su contraseña."
        )
        entrada_contrasena.focus()
        return

    conexion = conectar_bd()

    if conexion is None:
        return

    cursor = None

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SELECT
                u.id_usuario,
                u.nombre,
                u.usuario,
                u.id_rol,
                r.nombre_rol
            FROM usuarios u
            INNER JOIN roles r
                ON u.id_rol = r.id_rol
            WHERE u.usuario = %s
              AND u.contraseña = %s
              AND u.activo = 1
            """,
            (usuario, contrasena)
        )

        resultado = cursor.fetchone()

        if resultado is None:
            messagebox.showerror(
                "Acceso denegado",
                "El usuario o la contraseña son incorrectos,\n"
                "o el usuario se encuentra inactivo."
            )

            entrada_contrasena.delete(0, tk.END)
            entrada_contrasena.focus()
            return

        # Datos del usuario autenticado
        id_usuario = resultado[0]
        nombre_usuario = resultado[1]
        id_rol = resultado[3]
        nombre_rol = resultado[4]

        # Ruta del módulo principal
        ruta_llantas = os.path.join(
            os.path.dirname(__file__),
            "gestion_llantas.py"
        )

        # Abrir el módulo de llantas
        subprocess.Popen(
            [
                sys.executable,
                ruta_llantas,
                str(id_usuario),
                nombre_usuario,
                str(id_rol),
                nombre_rol
            ]
        )

        # Cerrar la ventana de login
        ventana.destroy()

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Error",
            f"No fue posible validar el usuario.\n\n{error}"
        )

    except Exception as error:
        messagebox.showerror(
            "Error",
            f"No fue posible abrir el módulo principal.\n\n{error}"
        )

    finally:
        if cursor is not None:
            cursor.close()

        conexion.close()


# ============================================================
# VENTANA PRINCIPAL
# ============================================================

ventana = tk.Tk()

ventana.title("Inicio de sesión - Gestión de Llantas")

# Ventana más amplia y alta
ancho_ventana = 500
alto_ventana = 540

# Centrar la ventana en la pantalla
ancho_pantalla = ventana.winfo_screenwidth()
alto_pantalla = ventana.winfo_screenheight()

posicion_x = (ancho_pantalla - ancho_ventana) // 2
posicion_y = (alto_pantalla - alto_ventana) // 2

ventana.geometry(
    f"{ancho_ventana}x{alto_ventana}+{posicion_x}+{posicion_y}"
)

ventana.resizable(False, False)
ventana.configure(background=COLOR_FONDO)


# ============================================================
# ENCABEZADO
# ============================================================

marco_encabezado = tk.Frame(
    ventana,
    background=COLOR_AZUL_OSCURO,
    height=125
)

marco_encabezado.pack(fill="x")
marco_encabezado.pack_propagate(False)

tk.Label(
    marco_encabezado,
    text="GESTIÓN Y CONTROL",
    font=("Arial", 20, "bold"),
    background=COLOR_AZUL_OSCURO,
    foreground=COLOR_BLANCO
).pack(pady=(24, 4))

tk.Label(
    marco_encabezado,
    text="Inventario de Llantas",
    font=("Arial", 12),
    background=COLOR_AZUL_OSCURO,
    foreground=COLOR_AZUL_CLARO
).pack()


# ============================================================
# PANEL DE LOGIN
# ============================================================

marco_login = tk.Frame(
    ventana,
    background=COLOR_BLANCO
)

marco_login.pack(
    padx=45,
    pady=25,
    fill="both",
    expand=True
)

tk.Label(
    marco_login,
    text="Iniciar sesión",
    font=("Arial", 16, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_AZUL_OSCURO
).pack(pady=(5, 22))


# ============================================================
# USUARIO
# ============================================================

tk.Label(
    marco_login,
    text="Usuario:",
    font=("Arial", 11, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_TEXTO
).pack(anchor="w")

entrada_usuario = ttk.Entry(
    marco_login,
    font=("Arial", 12)
)

entrada_usuario.pack(
    fill="x",
    ipady=7,
    pady=(7, 20)
)


# ============================================================
# CONTRASEÑA
# ============================================================

tk.Label(
    marco_login,
    text="Contraseña:",
    font=("Arial", 11, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_TEXTO
).pack(anchor="w")

entrada_contrasena = ttk.Entry(
    marco_login,
    show="*",
    font=("Arial", 12)
)

entrada_contrasena.pack(
    fill="x",
    ipady=7,
    pady=(7, 24)
)


# ============================================================
# ESTILO DEL BOTÓN
# ============================================================

estilo = ttk.Style()
estilo.theme_use("clam")

estilo.configure(
    "TButton",
    font=("Arial", 12, "bold"),
    padding=(24, 12),
    background=COLOR_AZUL,
    foreground=COLOR_BLANCO,
    borderwidth=0
)

estilo.map(
    "TButton",
    background=[
        ("active", COLOR_AZUL_OSCURO),
        ("pressed", COLOR_AZUL_OSCURO)
    ],
    foreground=[
        ("disabled", COLOR_BLANCO)
    ]
)


# ============================================================
# BOTÓN INGRESAR
# ============================================================

boton_ingresar = ttk.Button(
    marco_login,
    text="Ingresar",
    command=iniciar_sesion,
    width=18
)

boton_ingresar.pack(pady=5)


# ============================================================
# INFORMACIÓN
# ============================================================

tk.Label(
    marco_login,
    text="Ingrese sus credenciales para acceder al sistema.",
    font=("Arial", 9),
    background=COLOR_BLANCO,
    foreground=COLOR_GRIS
).pack(pady=(16, 5))


# ============================================================
# TECLA ENTER
# ============================================================

ventana.bind(
    "<Return>",
    lambda evento: iniciar_sesion()
)


# ============================================================
# INICIO
# ============================================================

entrada_usuario.focus()
ventana.mainloop()
