
import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
import subprocess
import sys
import os


# =========================================================
# CONFIGURACIÓN VISUAL
# =========================================================

COLOR_FONDO = "#F4F7FB"
COLOR_AZUL_OSCURO = "#1F4E78"
COLOR_AZUL = "#2F75B5"
COLOR_AZUL_CLARO = "#DCEAF7"
COLOR_BLANCO = "#FFFFFF"
COLOR_TEXTO = "#263238"
COLOR_GRIS = "#607D8B"
COLOR_GRIS_CLARO = "#E8EDF2"
COLOR_VERDE = "#2E7D32"
COLOR_ROJO = "#C62828"


# =========================================================
# ESTADOS Y UBICACIONES
# =========================================================

ESTADOS_VALIDOS = (
    "Stock",
    "Reencauche",
    "Ajuste/RM",
    "Garantía",
    "Desecho"
)

UBICACIONES_INICIALES = (
    "Contenedor",
    "Jaula"
)


# =========================================================
# DATOS DEL USUARIO AUTENTICADO
# =========================================================

id_usuario_recibido = ""
nombre_usuario_recibido = ""
id_rol_recibido = ""
nombre_rol_recibido = ""

if len(sys.argv) > 1:
    id_usuario_recibido = sys.argv[1]

if len(sys.argv) > 2:
    nombre_usuario_recibido = sys.argv[2]

if len(sys.argv) > 3:
    id_rol_recibido = sys.argv[3]

if len(sys.argv) > 4:
    nombre_rol_recibido = sys.argv[4]


# =========================================================
# CONEXIÓN CON LA BASE DE DATOS
# =========================================================

def obtener_conexion():
    return mysql.connector.connect(
        host="localhost",
        port=3307,
        user="root",
        password="",
        database="gestion_llantas"
    )


try:
    conexion = obtener_conexion()
except mysql.connector.Error as error:
    messagebox.showerror(
        "Error de conexión",
        "No fue posible conectar con la base de datos "
        "gestion_llantas.\n\n"
        f"{error}"
    )
    sys.exit(1)


# =========================================================
# VARIABLE PARA CONTROLAR LA CONSULTA
# =========================================================

llanta_consultada = False


# =========================================================
# COLOR SEGÚN EL ESTADO
# =========================================================

def obtener_color_estado(estado):
    colores = {
        "Rodando": "#00838F",
        "Stock": COLOR_VERDE,
        "Reencauche": "#EF6C00",
        "Ajuste/RM": "#B8860B",
        "Garantía": "#1565C0",
        "Desecho": COLOR_ROJO
        
    }

    return colores.get(estado, COLOR_GRIS)



# =========================================================
# CONSULTAR EL ESTADO ACTUAL DE UNA LLANTA
# =========================================================

def obtener_ultimo_estado(cursor, numero_llanta, ubicacion):
    # Una llanta instalada en un equipo está Rodando.
    if ubicacion == "Instalada en equipo":
        return "Rodando"

    cursor.execute(
        """
        SELECT estado
        FROM inspecciones
        WHERE numero_llanta = %s
        ORDER BY fecha_hora_inspeccion DESC, id_inspeccion DESC
        LIMIT 1
        """,
        (numero_llanta,)
    )

    resultado = cursor.fetchone()

    if resultado:
        return resultado[0]

    # Las llantas nuevas en estas ubicaciones se muestran como Stock.
    if ubicacion in UBICACIONES_INICIALES:
        return "Stock"

    return "Sin inspección previa"


# =========================================================
# FUNCIONES
# =========================================================

def consultar_llanta():
    global llanta_consultada

    numero = entrada_numero.get().strip()

    if not numero:
        messagebox.showwarning(
            "Dato requerido",
            "Ingrese el número de la llanta."
        )
        entrada_numero.focus()
        return

    cursor = None

    try:
        cursor = conexion.cursor()

        # -------------------------------------------------
        # CONSULTAR INFORMACIÓN DE LA LLANTA
        # -------------------------------------------------

        consulta = """
            SELECT
                l.numero_llanta,
                l.marca,
                l.diseño,
                l.diseño_reencauche,
                l.dimension,
                l.dot,
                a.nombre_almacen
            FROM llantas l
            INNER JOIN almacenes a
                ON l.id_almacen_actual = a.id_almacen
            WHERE l.numero_llanta = %s
        """

        cursor.execute(consulta, (numero,))
        llanta = cursor.fetchone()

        if not llanta:
            limpiar_informacion()

            etiqueta_estado_actual.config(
                text="Sin inspección previa",
                foreground=COLOR_GRIS
            )

            etiqueta_estado.config(
                text="Llanta no encontrada",
                foreground=COLOR_ROJO
            )

            llanta_consultada = False

            boton_inspeccion.config(state="disabled")

            messagebox.showwarning(
                "Llanta no encontrada",
                f"No existe una llanta registrada con el número "
                f"{numero}.\n\nPuede registrarla como nueva."
            )
            return

        # -------------------------------------------------
        # MOSTRAR INFORMACIÓN BÁSICA
        # -------------------------------------------------

        mostrar_informacion(
            llanta[1],
            llanta[2],
            llanta[3],
            llanta[4],
            llanta[5],
            llanta[6]
        )

        # -------------------------------------------------
        # MOSTRAR EL ESTADO ACTUAL
        # -------------------------------------------------

        estado_actual = obtener_ultimo_estado(
            cursor,
            llanta[0],
            llanta[6]
        )

        etiqueta_estado_actual.config(
            text=estado_actual,
            foreground=obtener_color_estado(estado_actual)
        )

        llanta_consultada = True

        boton_inspeccion.config(state="normal")

        etiqueta_estado.config(
            text="✓ La llanta existe",
            foreground=COLOR_VERDE
        )

    except mysql.connector.Error as error:
        llanta_consultada = False

        boton_inspeccion.config(state="disabled")

        messagebox.showerror(
            "Error de conexión",
            "No fue posible consultar la información.\n\n"
            f"{error}"
        )

    finally:
        if cursor is not None:
            cursor.close()


# =========================================================
# MOSTRAR INFORMACIÓN DE LA LLANTA
# =========================================================

def mostrar_informacion(
    marca,
    diseno,
    diseno_reencauche,
    dimension,
    dot,
    nombre_ubicacion
):
    # Son etiquetas informativas, no campos editables.
    entrada_marca.config(text=marca or "Sin información")
    entrada_diseno.config(text=diseno or "Sin información")
    entrada_diseno_reencauche.config(
        text=diseno_reencauche or ""
    )
    entrada_dimension.config(text=dimension or "Sin información")
    entrada_dot.config(text=dot or "Sin información")
    entrada_ubicacion.config(text=nombre_ubicacion or "No definida")


# =========================================================
# REGISTRAR NUEVA LLANTA
# =========================================================
def registrar_llanta():
    if str(id_rol_recibido) not in ("2", "3"):
        messagebox.showwarning(
            "Acceso restringido",
            "Solo los usuarios Analista e Ingeniero "
            "pueden registrar nuevas llantas."
        )
        return

    ruta_admin = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "modulo_administracion_llantas.py"
    )

    if not os.path.isfile(ruta_admin):
        messagebox.showerror(
            "Archivo no encontrado",
            "No se encontró modulo_administracion_llantas.py "
            "en la carpeta del proyecto."
        )
        return

    try:
        subprocess.Popen([
            sys.executable,
            ruta_admin,
            str(id_usuario_recibido),
            nombre_usuario_recibido,
            str(id_rol_recibido),
            nombre_rol_recibido
        ])
    except Exception as error:
        messagebox.showerror(
            "Error",
            f"No fue posible abrir el módulo.\n\n{error}"
        )


# =========================================================
# CONSULTA GENERAL POR UBICACIÓN
# =========================================================

def consultar_por_ubicacion():
    ventana_consulta = tk.Toplevel(ventana)
    ventana_consulta.title("Consulta por ubicación")
    ventana_consulta.geometry("760x500")
    ventana_consulta.resizable(False, False)
    ventana_consulta.configure(background=COLOR_FONDO)

    tk.Label(
        ventana_consulta,
        text="CONSULTA POR UBICACIÓN",
        font=("Arial", 16, "bold"),
        background=COLOR_AZUL_OSCURO,
        foreground=COLOR_BLANCO
    ).pack(fill="x", pady=(0, 15))

    marco_filtros = tk.Frame(
        ventana_consulta,
        background=COLOR_FONDO
    )
    marco_filtros.pack(fill="x", padx=20, pady=5)

    tk.Label(
        marco_filtros,
        text="Ubicación:",
        font=("Arial", 10, "bold"),
        background=COLOR_FONDO,
        foreground=COLOR_TEXTO
    ).pack(side="left", padx=(0, 10))

    combo_ubicacion_consulta = ttk.Combobox(
        marco_filtros,
        state="readonly",
        width=35
    )
    combo_ubicacion_consulta.pack(side="left", padx=(0, 10))

    cursor = None

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SELECT nombre_almacen
            FROM almacenes
            ORDER BY id_almacen
            """
        )

        ubicaciones = [fila[0] for fila in cursor.fetchall()]
        combo_ubicacion_consulta["values"] = ubicaciones

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Error de conexión",
            f"No fue posible cargar las ubicaciones.\n\n{error}",
            parent=ventana_consulta
        )
        ventana_consulta.destroy()
        return

    finally:
        if cursor is not None:
            cursor.close()

    etiqueta_resultado = tk.Label(
        ventana_consulta,
        text="Seleccione una ubicación para consultar.",
        font=("Arial", 10),
        background=COLOR_FONDO,
        foreground=COLOR_GRIS
    )
    etiqueta_resultado.pack(anchor="w", padx=20, pady=(15, 5))

    marco_tabla = tk.Frame(
        ventana_consulta,
        background=COLOR_FONDO
    )
    marco_tabla.pack(
        fill="both",
        expand=True,
        padx=20,
        pady=(0, 20)
    )

    columnas = ("numero", "marca", "dimension", "estado")

    tabla = ttk.Treeview(
        marco_tabla,
        columns=columnas,
        show="headings",
        height=14
    )

    tabla.heading("numero", text="Número")
    tabla.heading("marca", text="Marca")
    tabla.heading("dimension", text="Dimensión")
    tabla.heading("estado", text="Estado")

    tabla.column("numero", width=150)
    tabla.column("marca", width=140)
    tabla.column("dimension", width=150)
    tabla.column("estado", width=150)

    barra = ttk.Scrollbar(
        marco_tabla,
        orient="vertical",
        command=tabla.yview
    )

    tabla.configure(yscrollcommand=barra.set)

    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")

    def ejecutar_consulta():
        ubicacion = combo_ubicacion_consulta.get().strip()

        if not ubicacion:
            messagebox.showwarning(
                "Dato requerido",
                "Seleccione una ubicación.",
                parent=ventana_consulta
            )
            return

        for fila in tabla.get_children():
            tabla.delete(fila)

        cursor_consulta = None

        try:
            cursor_consulta = conexion.cursor()

            cursor_consulta.execute(
                """
                SELECT
                    l.numero_llanta,
                    l.marca,
                    l.dimension,
                    CASE
                    WHEN a.nombre_almacen = 'Instalada en equipo'
                        THEN 'Rodando'
                        WHEN ultima.estado IS NOT NULL
                            THEN ultima.estado
                        WHEN a.nombre_almacen IN ('Contenedor', 'Jaula')
                            THEN 'Stock'
                        ELSE 'Sin inspección previa'
                    END AS estado
                FROM llantas l
                INNER JOIN almacenes a
                    ON l.id_almacen_actual = a.id_almacen
                LEFT JOIN inspecciones ultima
                    ON ultima.id_inspeccion = (
                        SELECT i.id_inspeccion
                        FROM inspecciones i
                        WHERE i.numero_llanta = l.numero_llanta
                        ORDER BY
                            i.fecha_hora_inspeccion DESC,
                            i.id_inspeccion DESC
                        LIMIT 1
                    )
                WHERE a.nombre_almacen = %s
                ORDER BY l.numero_llanta
                """,
                (ubicacion,)
            )

            resultados = cursor_consulta.fetchall()

            for fila in resultados:
                tabla.insert("", tk.END, values=fila)

            etiqueta_resultado.config(
                text=f"Llantas encontradas: {len(resultados)}",
                foreground=COLOR_VERDE if resultados else COLOR_GRIS
            )

        except mysql.connector.Error as error:
            messagebox.showerror(
                "Error de conexión",
                f"No fue posible realizar la consulta.\n\n{error}",
                parent=ventana_consulta
            )

        finally:
            if cursor_consulta is not None:
                cursor_consulta.close()

    ttk.Button(
        marco_filtros,
        text="Consultar",
        command=ejecutar_consulta
    ).pack(side="left")


# =========================================================
# CONSULTA GENERAL POR ESTADO
# =========================================================

def consultar_por_estado():
    ventana_consulta = tk.Toplevel(ventana)
    ventana_consulta.title("Consulta por estado")
    ventana_consulta.geometry("760x500")
    ventana_consulta.resizable(False, False)
    ventana_consulta.configure(background=COLOR_FONDO)

    tk.Label(
        ventana_consulta,
        text="CONSULTA POR ESTADO",
        font=("Arial", 16, "bold"),
        background=COLOR_AZUL_OSCURO,
        foreground=COLOR_BLANCO
    ).pack(fill="x", pady=(0, 15))

    marco_filtros = tk.Frame(
        ventana_consulta,
        background=COLOR_FONDO
    )
    marco_filtros.pack(fill="x", padx=20, pady=5)

    tk.Label(
        marco_filtros,
        text="Estado:",
        font=("Arial", 10, "bold"),
        background=COLOR_FONDO,
        foreground=COLOR_TEXTO
    ).pack(side="left", padx=(0, 10))

    combo_estado_consulta = ttk.Combobox(
        marco_filtros,
        values=list(ESTADOS_VALIDOS),
        state="readonly",
        width=25
    )
    combo_estado_consulta.pack(side="left", padx=(0, 10))

    etiqueta_resultado = tk.Label(
        ventana_consulta,
        text="Seleccione un estado para consultar.",
        font=("Arial", 10),
        background=COLOR_FONDO,
        foreground=COLOR_GRIS
    )
    etiqueta_resultado.pack(anchor="w", padx=20, pady=(15, 5))

    marco_tabla = tk.Frame(
        ventana_consulta,
        background=COLOR_FONDO
    )
    marco_tabla.pack(
        fill="both",
        expand=True,
        padx=20,
        pady=(0, 20)
    )

    columnas = ("numero", "marca", "dimension", "ubicacion")

    tabla = ttk.Treeview(
        marco_tabla,
        columns=columnas,
        show="headings",
        height=14
    )

    tabla.heading("numero", text="Número")
    tabla.heading("marca", text="Marca")
    tabla.heading("dimension", text="Dimensión")
    tabla.heading("ubicacion", text="Ubicación")

    tabla.column("numero", width=150)
    tabla.column("marca", width=140)
    tabla.column("dimension", width=150)
    tabla.column("ubicacion", width=180)

    barra = ttk.Scrollbar(
        marco_tabla,
        orient="vertical",
        command=tabla.yview
    )

    tabla.configure(yscrollcommand=barra.set)

    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")

    def ejecutar_consulta():
        estado = combo_estado_consulta.get().strip()

        if not estado:
            messagebox.showwarning(
                "Dato requerido",
                "Seleccione un estado.",
                parent=ventana_consulta
            )
            return

        for fila in tabla.get_children():
            tabla.delete(fila)

        cursor_consulta = None

        try:
            cursor_consulta = conexion.cursor()

            cursor_consulta.execute(
                """
                SELECT
                    l.numero_llanta,
                    l.marca,
                    l.dimension,
                    a.nombre_almacen
                FROM llantas l
                INNER JOIN almacenes a
                    ON l.id_almacen_actual = a.id_almacen
                LEFT JOIN inspecciones ultima
                    ON ultima.id_inspeccion = (
                        SELECT i.id_inspeccion
                        FROM inspecciones i
                        WHERE i.numero_llanta = l.numero_llanta
                        ORDER BY
                            i.fecha_hora_inspeccion DESC,
                            i.id_inspeccion DESC
                        LIMIT 1
                    )
                WHERE
                    ultima.estado = %s
                    OR (
                        %s = 'Stock'
                        AND ultima.id_inspeccion IS NULL
                        AND a.nombre_almacen IN ('Contenedor', 'Jaula')
                    )
                ORDER BY l.numero_llanta
                """,
                (estado, estado)
            )

            resultados = cursor_consulta.fetchall()

            for fila in resultados:
                tabla.insert("", tk.END, values=fila)

            etiqueta_resultado.config(
                text=f"Llantas en {estado}: {len(resultados)}",
                foreground=obtener_color_estado(estado)
            )

        except mysql.connector.Error as error:
            messagebox.showerror(
                "Error de conexión",
                f"No fue posible realizar la consulta.\n\n{error}",
                parent=ventana_consulta
            )

        finally:
            if cursor_consulta is not None:
                cursor_consulta.close()

    ttk.Button(
        marco_filtros,
        text="Consultar",
        command=ejecutar_consulta
    ).pack(side="left")


# =========================================================
# GENERAR NUEVA INSPECCIÓN
# =========================================================

def generar_nueva_inspeccion():
    global llanta_consultada

    if not llanta_consultada:
        messagebox.showwarning(
            "Consulta requerida",
            "Primero consulte una llanta antes de generar "
            "una nueva inspección."
        )
        return

    numero = entrada_numero.get().strip()

    if not numero:
        messagebox.showwarning(
            "Llanta requerida",
            "Primero consulte una llanta para generar "
            "una nueva inspección."
        )
        entrada_numero.focus()
        return

    ruta_inspecciones = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "modulo_inspecciones.py"
    )

    if not os.path.isfile(ruta_inspecciones):
        messagebox.showerror(
            "Archivo no encontrado",
            "No se encontró el archivo modulo_inspecciones.py "
            "en la carpeta del proyecto."
        )
        return

    try:
        subprocess.Popen(
            [
                sys.executable,
                ruta_inspecciones,
                numero,
                str(id_usuario_recibido),
                nombre_usuario_recibido,
                str(id_rol_recibido),
                nombre_rol_recibido,
                str(os.getpid())
            ]
        )

    except Exception as error:
        messagebox.showerror(
            "Error",
            "No fue posible abrir el módulo de inspecciones.\n\n"
            f"{error}"
        )


# =========================================================
# CERRAR SESIÓN
# =========================================================

def cerrar_sesion():
    respuesta = messagebox.askyesno(
        "Cerrar sesión",
        "¿Está seguro de que desea cerrar sesión?"
    )

    if not respuesta:
        return

    ruta_login = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "login.py"
    )

    if not os.path.isfile(ruta_login):
        messagebox.showerror(
            "Archivo no encontrado",
            "No se encontró el archivo login.py."
        )
        return

    try:
        subprocess.Popen([sys.executable, ruta_login])
    except Exception as error:
        messagebox.showerror(
            "Error",
            f"No fue posible volver al inicio de sesión.\n\n{error}"
        )
        return

    try:
        conexion.close()
    except mysql.connector.Error:
        pass

    ventana.destroy()


# =========================================================
# LIMPIAR INFORMACIÓN
# =========================================================

def limpiar_informacion():
    entrada_marca.config(text="Sin información")
    entrada_diseno.config(text="Sin información")
    entrada_diseno_reencauche.config(text="Sin información")
    entrada_dimension.config(text="Sin información")
    entrada_dot.config(text="Sin información")
    entrada_ubicacion.config(text="Sin información")


# =========================================================
# LIMPIAR CAMPOS
# =========================================================

def limpiar_campos():
    global llanta_consultada

    llanta_consultada = False

    entrada_numero.delete(0, tk.END)

    limpiar_informacion()

    etiqueta_estado_actual.config(
        text="Sin inspección previa",
        foreground=COLOR_GRIS
    )

    etiqueta_estado.config(
        text="Ingrese un número para consultar",
        foreground=COLOR_GRIS
    )

    boton_inspeccion.config(state="disabled")

    entrada_numero.focus()


# =========================================================
# VENTANA PRINCIPAL
# =========================================================

ventana = tk.Tk()

ventana.title("Módulo de Gestión de Llantas")
ventana.geometry("900x700")
ventana.resizable(False, False)
ventana.configure(background=COLOR_FONDO)


# =========================================================
# ESTILOS ttk
# =========================================================

estilo = ttk.Style()
estilo.theme_use("clam")

estilo.configure(
    "TButton",
    font=("Arial", 10, "bold"),
    padding=(12, 8),
    background=COLOR_AZUL,
    foreground=COLOR_BLANCO,
    borderwidth=0
)

estilo.map(
    "TButton",
    background=[
        ("active", COLOR_AZUL_OSCURO),
        ("disabled", COLOR_GRIS_CLARO)
    ],
    foreground=[
        ("active", COLOR_BLANCO),
        ("disabled", COLOR_GRIS)
    ]
)

estilo.configure(
    "TEntry",
    font=("Arial", 10),
    padding=7
)

estilo.configure(
    "Panel.TLabelframe",
    background=COLOR_BLANCO,
    bordercolor=COLOR_GRIS_CLARO,
    relief="solid"
)

estilo.configure(
    "Panel.TLabelframe.Label",
    background=COLOR_BLANCO,
    foreground=COLOR_AZUL_OSCURO,
    font=("Arial", 11, "bold")
)


# =========================================================
# ENCABEZADO
# =========================================================

marco_encabezado = tk.Frame(
    ventana,
    background=COLOR_AZUL_OSCURO,
    height=115
)

marco_encabezado.pack(fill="x")
marco_encabezado.pack_propagate(False)


# =========================================================
# BOTÓN CERRAR SESIÓN
# =========================================================

boton_cerrar_sesion = tk.Button(
    marco_encabezado,
    text="Cerrar sesión",
    command=cerrar_sesion,
    bg=COLOR_ROJO,
    fg=COLOR_BLANCO,
    activebackground="#8E0000",
    activeforeground=COLOR_BLANCO,
    font=("Arial", 10, "bold"),
    relief="flat",
    padx=10,
    pady=5,
    cursor="hand2"
)

boton_cerrar_sesion.pack(
    side="right",
    padx=15,
    pady=10
)


titulo = tk.Label(
    marco_encabezado,
    text="MODULO DE GESTION DE LLANTAS",
    font=("Arial", 20, "bold"),
    background=COLOR_AZUL_OSCURO,
    foreground=COLOR_BLANCO
)

titulo.pack(pady=(22, 8))


# =========================================================
# BIENVENIDA DEL USUARIO
# =========================================================

texto_bienvenida = (
    f"Bienvenido, {nombre_usuario_recibido}"
    if nombre_usuario_recibido
    else "Bienvenido"
)

bienvenida = tk.Label(
    marco_encabezado,
    text=texto_bienvenida,
    font=("Arial", 15, "bold"),
    background=COLOR_AZUL_OSCURO,
    foreground=COLOR_BLANCO
)

bienvenida.pack()


# =========================================================
# PANEL PRINCIPAL
# =========================================================

marco_principal = tk.Frame(
    ventana,
    background=COLOR_BLANCO
)

marco_principal.pack(
    padx=40,
    pady=25,
    fill="both",
    expand=True
)


# =========================================================
# DISTRIBUCIÓN PRINCIPAL
# =========================================================

marco_contenido = tk.Frame(
    marco_principal,
    background=COLOR_BLANCO
)

marco_contenido.pack(fill="both", expand=True)

marco_informacion_principal = tk.Frame(
    marco_contenido,
    background=COLOR_BLANCO
)

marco_informacion_principal.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(0, 20)
)

marco_botones_lateral = tk.Frame(
    marco_contenido,
    background=COLOR_BLANCO,
    width=210
)

marco_botones_lateral.pack(
    side="right",
    fill="y"
)

marco_botones_lateral.pack_propagate(False)


# =========================================================
# INFORMACIÓN DE LA LLANTA
# =========================================================

marco = ttk.LabelFrame(
    marco_informacion_principal,
    text="  Información de la llanta  ",
    style="Panel.TLabelframe",
    padding=18
)

marco.pack(fill="both", expand=True)


# =========================================================
# NÚMERO DE LLANTA
# =========================================================

tk.Label(
    marco,
    text="Número de llanta:",
    font=("Arial", 10, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_TEXTO
).grid(row=0, column=0, sticky="w", pady=9)

entrada_numero = ttk.Entry(marco, width=35)

entrada_numero.grid(
    row=0,
    column=1,
    padx=15,
    pady=9
)


# =========================================================
# ESTADO DE CONSULTA
# =========================================================

etiqueta_estado = tk.Label(
    marco,
    text="Ingrese un número para consultar",
    font=("Arial", 9),
    background=COLOR_BLANCO,
    foreground=COLOR_GRIS
)

etiqueta_estado.grid(
    row=1,
    column=1,
    sticky="w",
    padx=15,
    pady=(0, 10)
)


# =========================================================
# ESTADO ACTUAL
# =========================================================

tk.Label(
    marco,
    text="Estado actual:",
    font=("Arial", 10, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_TEXTO
).grid(row=2, column=0, sticky="w", pady=9)

etiqueta_estado_actual = tk.Label(
    marco,
    text="Sin inspección previa",
    font=("Arial", 11, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_GRIS
)

etiqueta_estado_actual.grid(
    row=2,
    column=1,
    sticky="w",
    padx=15,
    pady=9
)


# =========================================================
# UBICACIÓN ACTUAL
# =========================================================

tk.Label(
    marco,
    text="Ubicación actual:",
    font=("Arial", 10, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_TEXTO
).grid(row=3, column=0, sticky="w", pady=9)

entrada_ubicacion = tk.Label(
    marco,
    text="Sin información",
    anchor="w",
    font=("Arial", 11, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_VERDE
)

entrada_ubicacion.grid(
    row=3,
    column=1,
    sticky="w",
    padx=15,
    pady=9
)


# =========================================================
# MARCA
# =========================================================

tk.Label(
    marco,
    text="Marca:",
    font=("Arial", 10),
    background=COLOR_BLANCO,
    foreground=COLOR_TEXTO
).grid(row=4, column=0, sticky="w", pady=9)

entrada_marca = tk.Label(
    marco,
    text="Sin información",
    anchor="w",
    font=("Arial", 11, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_VERDE
)

entrada_marca.grid(
    row=4,
    column=1,
    sticky="w",
    padx=15,
    pady=9
)


# =========================================================
# DISEÑO
# =========================================================

tk.Label(
    marco,
    text="Diseño:",
    font=("Arial", 10),
    background=COLOR_BLANCO,
    foreground=COLOR_TEXTO
).grid(row=5, column=0, sticky="w", pady=9)

entrada_diseno = tk.Label(
    marco,
    text="Sin información",
    anchor="w",
    font=("Arial", 11, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_VERDE
)

entrada_diseno.grid(
    row=5,
    column=1,
    sticky="w",
    padx=15,
    pady=9
)


# =========================================================
# DISEÑO DE REENCAUCHE
# =========================================================

tk.Label(
    marco,
    text="Diseño de reencauche:",
    font=("Arial", 10),
    background=COLOR_BLANCO,
    foreground=COLOR_TEXTO
).grid(row=6, column=0, sticky="w", pady=9)

entrada_diseno_reencauche = tk.Label(
    marco,
    text="Sin información",
    anchor="w",
    font=("Arial", 11, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_VERDE
)

entrada_diseno_reencauche.grid(
    row=6,
    column=1,
    sticky="w",
    padx=15,
    pady=9
)


# =========================================================
# DIMENSIÓN
# =========================================================

tk.Label(
    marco,
    text="Dimensión:",
    font=("Arial", 10),
    background=COLOR_BLANCO,
    foreground=COLOR_TEXTO
).grid(row=7, column=0, sticky="w", pady=9)

entrada_dimension = tk.Label(
    marco,
    text="Sin información",
    anchor="w",
    font=("Arial", 11, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_VERDE
)

entrada_dimension.grid(
    row=7,
    column=1,
    sticky="w",
    padx=15,
    pady=9
)


# =========================================================
# DOT
# =========================================================

tk.Label(
    marco,
    text="DOT:",
    font=("Arial", 10),
    background=COLOR_BLANCO,
    foreground=COLOR_TEXTO
).grid(row=8, column=0, sticky="w", pady=9)

entrada_dot = tk.Label(
    marco,
    text="Sin información",
    anchor="w",
    font=("Arial", 11, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_VERDE
)

entrada_dot.grid(
    row=8,
    column=1,
    sticky="w",
    padx=15,
    pady=9
)


# =========================================================
# BOTONES LATERALES
# =========================================================

tk.Label(
    marco_botones_lateral,
    text="ACCIONES",
    font=("Arial", 11, "bold"),
    background=COLOR_BLANCO,
    foreground=COLOR_AZUL_OSCURO
).pack(pady=(5, 15))


# =========================================================
# BOTÓN CONSULTAR
# =========================================================

boton_consultar = ttk.Button(
    marco_botones_lateral,
    text="Consultar",
    command=consultar_llanta,
    width=22
)

boton_consultar.pack(fill="x", pady=5)


# =========================================================
# BOTÓN CONSULTAR POR UBICACIÓN
# =========================================================

boton_ubicacion = ttk.Button(
    marco_botones_lateral,
    text="Consultar por ubicación",
    command=consultar_por_ubicacion,
    width=22
)

boton_ubicacion.pack(fill="x", pady=5)


# =========================================================
# BOTÓN CONSULTAR POR ESTADO
# =========================================================

boton_estado_consulta = ttk.Button(
    marco_botones_lateral,
    text="Consultar por estado",
    command=consultar_por_estado,
    width=22
)

boton_estado_consulta.pack(fill="x", pady=5)


# =========================================================
# BOTÓN NUEVA INSPECCIÓN
# =========================================================

boton_inspeccion = ttk.Button(
    marco_botones_lateral,
    text="Generar nueva inspección",
    command=generar_nueva_inspeccion,
    width=22,
    state="disabled"
)

boton_inspeccion.pack(fill="x", pady=5)


# =========================================================
# BOTÓN REGISTRAR NUEVA LLANTA
# =========================================================

boton_registrar = ttk.Button(
    marco_botones_lateral,
    text="Registrar nueva llanta",
    command=registrar_llanta,
    width=22
)

boton_registrar.pack(fill="x", pady=5)


# =========================================================
# PERMISOS DEL BOTÓN DE REGISTRO
# =========================================================

if str(id_rol_recibido) not in ("2", "3"):
    boton_registrar.pack_forget()


# =========================================================
# BOTÓN LIMPIAR
# =========================================================

boton_limpiar = ttk.Button(
    marco_botones_lateral,
    text="Limpiar campos",
    command=limpiar_campos,
    width=22
)

boton_limpiar.pack(fill="x", pady=(20, 5))


# =========================================================
# CIERRE SEGURO DE LA VENTANA
# =========================================================

def al_cerrar_ventana():
    try:
        if conexion.is_connected():
            conexion.close()
    except mysql.connector.Error:
        pass

    ventana.destroy()


ventana.protocol("WM_DELETE_WINDOW", al_cerrar_ventana)


# =========================================================
# INICIO DE LA APLICACIÓN
# =========================================================

entrada_numero.focus()
ventana.mainloop()
