
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import mysql.connector
import os
import shutil
import sys
import subprocess


# ============================================================
# COLORES
# ============================================================

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
COLOR_ROJO_CLARO = "#FFCCCC"


# ============================================================
# CONFIGURACIÓN
# ============================================================

ESTADOS = [
    "Stock",
    "Reencauche",
    "Ajuste/RM",
    "Garantía",
    "Desecho"
]

MIN_FOTOS = 4
MAX_FOTOS = 5
LIMITE_PROFUNDIDAD = 3.0

DESTINOS_VALIDOS = [
    "Rack de Stock",
    "Pila para Reencauche",
    "Pila Ajuste/RM",
    "Pila de Desecho",
    "Rack Garantías"
]

DESTINOS_POR_ESTADO = {
    "Stock": "Rack de Stock",
    "Reencauche": "Pila para Reencauche",
    "Ajuste/RM": "Pila Ajuste/RM",
    "Garantía": "Rack Garantías",
    "Desecho": "Pila de Desecho"
}


# ============================================================
# DATOS RECIBIDOS DESDE MODULO LLANTAS
# ============================================================

numero_recibido = sys.argv[1] if len(sys.argv) > 1 else ""
id_usuario_recibido = sys.argv[2] if len(sys.argv) > 2 else ""
nombre_usuario_recibido = sys.argv[3] if len(sys.argv) > 3 else ""
id_rol_recibido = sys.argv[4] if len(sys.argv) > 4 else ""
nombre_rol_recibido = sys.argv[5] if len(sys.argv) > 5 else ""

pid_modulo_llantas = sys.argv[6] if len(sys.argv) > 6 else ""


# ============================================================
# VARIABLES
# ============================================================

estado_anterior_recibido = "Sin inspección previa"

profundidad_externa_anterior = "Sin dato"
profundidad_central_anterior = "Sin dato"
profundidad_interna_anterior = "Sin dato"

lista_fotos = []

valor_numero = None
valor_usuario = None
valor_estado_anterior = None

valor_profundidad_externa_anterior = None
valor_profundidad_central_anterior = None
valor_profundidad_interna_anterior = None

combo_estado = None
combo_almacen = None

entrada_profundidad_externa = None
entrada_profundidad_central = None
entrada_profundidad_interna = None

entrada_observaciones = None

etiqueta_fotos = None
etiqueta_estado_anterior = None


# ============================================================
# CONEXIÓN A LA BASE DE DATOS
# ============================================================

def conectar_bd():
    return mysql.connector.connect(
        host="localhost",
        port=3307,
        user="root",
        password="",
        database="gestion_llantas"
    )


# ============================================================
# COLOR DEL ESTADO ANTERIOR
# ============================================================

def actualizar_color_estado_anterior(*args):
    if etiqueta_estado_anterior is None:
        return

    estado = valor_estado_anterior.get()

    colores_estados = {
        "Stock": "#2E7D32",
        "Reencauche": "#EF6C00",
        "Ajuste/RM": "#B8860B",
        "Garantía": "#1565C0",
        "Desecho": "#C62828",
        "Sin inspección previa": "#607D8B"
    }

    etiqueta_estado_anterior.config(
        fg=colores_estados.get(estado, COLOR_GRIS)
    )


# ============================================================
# CARGAR DATOS DE LA LLANTA
# ============================================================

def cargar_datos_llanta():
    global estado_anterior_recibido
    global profundidad_externa_anterior
    global profundidad_central_anterior
    global profundidad_interna_anterior

    conexion = None
    cursor = None

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor()

        # ----------------------------------------------------
        # Verificar que la llanta exista y consultar ubicación
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                l.numero_llanta,
                a.nombre_almacen
            FROM llantas l
            INNER JOIN almacenes a
                ON l.id_almacen_actual = a.id_almacen
            WHERE l.numero_llanta = %s
            """,
            (numero_recibido,)
        )

        resultado_llanta = cursor.fetchone()

        if not resultado_llanta:
            messagebox.showerror(
                "Error",
                "La llanta indicada no existe en la base de datos."
            )
            ventana.destroy()
            return

        valor_numero.set(resultado_llanta[0])
        ubicacion_actual = resultado_llanta[1]

        # ----------------------------------------------------
        # Buscar la última inspección
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                estado,
                profundidad_externa,
                profundidad_central,
                profundidad_interna
            FROM inspecciones
            WHERE numero_llanta = %s
            ORDER BY
                fecha_hora_inspeccion DESC,
                id_inspeccion DESC
            LIMIT 1
            """,
            (numero_recibido,)
        )

        resultado = cursor.fetchone()

        if resultado:
            estado_anterior_recibido = (
                resultado[0]
                if resultado[0] is not None
                else "Sin inspección previa"
            )

            profundidad_externa_anterior = (
                str(resultado[1])
                if resultado[1] is not None
                else "Sin dato"
            )

            profundidad_central_anterior = (
                str(resultado[2])
                if resultado[2] is not None
                else "Sin dato"
            )

            profundidad_interna_anterior = (
                str(resultado[3])
                if resultado[3] is not None
                else "Sin dato"
            )

        else:
            # Las llantas nuevas en Contenedor o Jaula se
            # muestran como Stock aunque no tengan inspección.
            if ubicacion_actual in ("Contenedor", "Jaula"):
                estado_anterior_recibido = "Stock"
            else:
                estado_anterior_recibido = "Sin inspección previa"

            profundidad_externa_anterior = "Sin dato"
            profundidad_central_anterior = "Sin dato"
            profundidad_interna_anterior = "Sin dato"

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Error de conexión",
            "No fue posible cargar los datos de la llanta.\n\n"
            f"{error}"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()


# ============================================================
# CARGAR DESTINOS VÁLIDOS
# ============================================================

def cargar_almacenes():
    conexion = None
    cursor = None

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor()

        cursor.execute(
            """
            SELECT nombre_almacen
            FROM almacenes
            WHERE nombre_almacen IN (%s, %s, %s, %s, %s)
            ORDER BY id_almacen
            """,
            tuple(DESTINOS_VALIDOS)
        )

        resultados = cursor.fetchall()

        destinos_en_bd = [fila[0] for fila in resultados]

        combo_almacen["values"] = destinos_en_bd

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Error",
            f"No fue posible cargar los destinos.\n\n{error}"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()


# ============================================================
# SELECCIONAR DESTINO SEGÚN EL ESTADO
# ============================================================

def actualizar_destino_estado(event=None):
    estado = combo_estado.get().strip()

    destino = DESTINOS_POR_ESTADO.get(estado)

    if destino:
        destinos_disponibles = list(combo_almacen["values"])

        if destino in destinos_disponibles:
            combo_almacen.set(destino)
        else:
            combo_almacen.set("")
    else:
        combo_almacen.set("")

    actualizar_estado_fotos()


# ============================================================
# COLOR DE PROFUNDIDADES
# ============================================================

def actualizar_color_profundidad(event=None):
    entradas = [
        entrada_profundidad_externa,
        entrada_profundidad_central,
        entrada_profundidad_interna
    ]

    for entrada in entradas:
        if entrada is None:
            continue

        valor = entrada.get().strip()

        if valor == "":
            entrada.config(
                bg=COLOR_BLANCO,
                fg=COLOR_TEXTO
            )
            continue

        try:
            profundidad = float(valor)

            if profundidad < 0:
                entrada.config(
                    bg=COLOR_ROJO_CLARO,
                    fg=COLOR_ROJO
                )
            elif profundidad < LIMITE_PROFUNDIDAD:
                entrada.config(
                    bg=COLOR_ROJO_CLARO,
                    fg=COLOR_ROJO
                )
            else:
                entrada.config(
                    bg=COLOR_BLANCO,
                    fg=COLOR_TEXTO
                )

        except ValueError:
            entrada.config(
                bg=COLOR_ROJO_CLARO,
                fg=COLOR_ROJO
            )


# ============================================================
# ACTUALIZAR ESTADO DE FOTOS
# ============================================================

def actualizar_estado_fotos(event=None):
    if etiqueta_fotos is None:
        return

    cantidad = len(lista_fotos)

    if combo_estado.get() == "Desecho":
        etiqueta_fotos.config(
            text=(
                f"Evidencias seleccionadas: {cantidad} / "
                f"{MIN_FOTOS}-{MAX_FOTOS}"
            ),
            fg=COLOR_ROJO if cantidad < MIN_FOTOS else COLOR_VERDE
        )
    else:
        etiqueta_fotos.config(
            text=f"Evidencias seleccionadas: {cantidad}",
            fg=COLOR_GRIS
        )


# ============================================================
# SELECCIONAR FOTOS
# ============================================================

def seleccionar_fotos():
    global lista_fotos

    archivos = filedialog.askopenfilenames(
        title="Seleccionar evidencias",
        filetypes=[
            ("Imágenes JPG, JPEG y PNG", "*.jpg *.jpeg *.png")
        ]
    )

    if not archivos:
        return

    archivos_validos = []

    for archivo in archivos:
        extension = os.path.splitext(archivo)[1].lower()

        if extension in (".jpg", ".jpeg", ".png"):
            archivos_validos.append(archivo)

    # Evitar seleccionar más del máximo permitido.
    if len(archivos_validos) > MAX_FOTOS:
        messagebox.showwarning(
            "Límite de evidencias",
            f"Solo puede seleccionar máximo {MAX_FOTOS} fotografías."
        )
        archivos_validos = archivos_validos[:MAX_FOTOS]

    lista_fotos = list(archivos_validos)

    actualizar_estado_fotos()


# ============================================================
# LIMPIAR CAMPOS
# ============================================================

def limpiar_campos():
    combo_estado.set("")
    combo_almacen.set("")

    entrada_profundidad_externa.delete(0, tk.END)
    entrada_profundidad_central.delete(0, tk.END)
    entrada_profundidad_interna.delete(0, tk.END)

    entrada_profundidad_externa.config(
        bg=COLOR_BLANCO,
        fg=COLOR_TEXTO
    )

    entrada_profundidad_central.config(
        bg=COLOR_BLANCO,
        fg=COLOR_TEXTO
    )

    entrada_profundidad_interna.config(
        bg=COLOR_BLANCO,
        fg=COLOR_TEXTO
    )

    entrada_observaciones.delete("1.0", tk.END)

    lista_fotos.clear()

    actualizar_estado_fotos()


# ============================================================
# REGISTRAR INSPECCIÓN
# ============================================================

def registrar_inspeccion():
    numero_llanta = valor_numero.get().strip()
    nombre_inspector = nombre_usuario_recibido.strip()

    estado = combo_estado.get().strip()
    almacen_destino = combo_almacen.get().strip()

    profundidad_externa_texto = (
        entrada_profundidad_externa.get().strip()
    )
    profundidad_central_texto = (
        entrada_profundidad_central.get().strip()
    )
    profundidad_interna_texto = (
        entrada_profundidad_interna.get().strip()
    )

    observaciones = entrada_observaciones.get(
        "1.0",
        tk.END
    ).strip()

    # --------------------------------------------------------
    # Validaciones básicas
    # --------------------------------------------------------

    if not numero_llanta:
        messagebox.showwarning(
            "Dato faltante",
            "No se encontró el número de llanta."
        )
        return

    if not nombre_inspector:
        messagebox.showwarning(
            "Dato faltante",
            "No se encontró el inspector."
        )
        return

    try:
        id_usuario = int(id_usuario_recibido)
    except (TypeError, ValueError):
        messagebox.showwarning(
            "Usuario no identificado",
            "No se encontró un usuario autenticado válido."
        )
        return

    if not estado:
        messagebox.showwarning(
            "Dato faltante",
            "Seleccione el estado de la llanta."
        )
        return

    if estado not in ESTADOS:
        messagebox.showwarning(
            "Estado inválido",
            "Seleccione un estado válido."
        )
        return

    if not almacen_destino:
        messagebox.showwarning(
            "Dato faltante",
            "Seleccione el destino de la llanta."
        )
        return

    # --------------------------------------------------------
    # Validar correspondencia entre estado y destino
    # --------------------------------------------------------

    destino_correcto = DESTINOS_POR_ESTADO[estado]

    if almacen_destino != destino_correcto:
        messagebox.showwarning(
            "Destino incorrecto",
            f"El estado {estado} debe enviarse a:\n\n"
            f"{destino_correcto}\n\n"
            "Seleccione el estado nuevamente para asignar "
            "automáticamente su destino."
        )
        return

    # --------------------------------------------------------
    # Validar profundidades
    # --------------------------------------------------------

    if (
        not profundidad_externa_texto
        or not profundidad_central_texto
        or not profundidad_interna_texto
    ):
        messagebox.showwarning(
            "Dato faltante",
            "Ingrese las tres profundidades."
        )
        return

    try:
        profundidad_externa = float(profundidad_externa_texto)
        profundidad_central = float(profundidad_central_texto)
        profundidad_interna = float(profundidad_interna_texto)

        profundidades = [
            profundidad_externa,
            profundidad_central,
            profundidad_interna
        ]

        if any(valor < 0 for valor in profundidades):
            messagebox.showwarning(
                "Dato inválido",
                "Las profundidades no pueden ser negativas."
            )
            return

    except ValueError:
        messagebox.showwarning(
            "Dato inválido",
            "Las profundidades deben ser valores numéricos."
        )
        return

    # --------------------------------------------------------
    # Validar fotografías para Desecho
    # --------------------------------------------------------

    if estado == "Desecho":
        if not MIN_FOTOS <= len(lista_fotos) <= MAX_FOTOS:
            messagebox.showwarning(
                "Evidencias requeridas",
                f"Para registrar una llanta como Desecho debe "
                f"adjuntar entre {MIN_FOTOS} y {MAX_FOTOS} fotografías."
            )
            return

    # --------------------------------------------------------
    # Conectar y registrar
    # --------------------------------------------------------

    conexion = None
    cursor = None
    archivos_copiados = []

    try:
        conexion = conectar_bd()
        conexion.start_transaction()
        cursor = conexion.cursor()

        # Verificar que la llanta exista.
        cursor.execute(
            """
            SELECT numero_llanta
            FROM llantas
            WHERE numero_llanta = %s
            """,
            (numero_llanta,)
        )

        if not cursor.fetchone():
            raise ValueError("La llanta no existe en la base de datos.")

        # Verificar que el usuario exista y esté activo.
        cursor.execute(
            """
            SELECT id_usuario
            FROM usuarios
            WHERE id_usuario = %s
              AND activo = 1
            """,
            (id_usuario,)
        )

        if not cursor.fetchone():
            raise ValueError(
                "El usuario no existe o está inactivo."
            )

        # Obtener el ID del destino.
        cursor.execute(
            """
            SELECT id_almacen
            FROM almacenes
            WHERE nombre_almacen = %s
            """,
            (almacen_destino,)
        )

        resultado_almacen = cursor.fetchone()

        if not resultado_almacen:
            raise ValueError(
                "No se encontró el destino seleccionado "
                "en la tabla almacenes."
            )

        id_almacen_destino = resultado_almacen[0]

        # ----------------------------------------------------
        # Insertar inspección
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO inspecciones (
                numero_llanta,
                id_usuario,
                fecha_hora_inspeccion,
                profundidad_externa,
                profundidad_central,
                profundidad_interna,
                estado,
                observaciones,
                id_almacen_destino
            )
            VALUES (
                %s, %s, NOW(), %s, %s, %s, %s, %s, %s
            )
            """,
            (
                numero_llanta,
                id_usuario,
                profundidad_externa,
                profundidad_central,
                profundidad_interna,
                estado,
                observaciones,
                id_almacen_destino
            )
        )

        id_inspeccion = cursor.lastrowid

        # ----------------------------------------------------
        # Actualizar ubicación actual de la llanta
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE llantas
            SET id_almacen_actual = %s
            WHERE numero_llanta = %s
            """,
            (
                id_almacen_destino,
                numero_llanta
            )
        )

        # ----------------------------------------------------
        # Guardar evidencias fotográficas
        # ----------------------------------------------------

        if lista_fotos:
            carpeta_evidencias = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "evidencias"
            )

            os.makedirs(
                carpeta_evidencias,
                exist_ok=True
            )

            for indice, archivo in enumerate(lista_fotos, start=1):
                extension = os.path.splitext(archivo)[1].lower()

                if extension not in (".jpg", ".jpeg", ".png"):
                    raise ValueError(
                        "Las evidencias deben ser archivos JPG, "
                        "JPEG o PNG."
                    )

                nombre_archivo = (
                    f"{numero_llanta}_"
                    f"inspeccion_{id_inspeccion}_"
                    f"evidencia_{indice}{extension}"
                )

                destino_archivo = os.path.join(
                    carpeta_evidencias,
                    nombre_archivo
                )

                shutil.copy2(archivo, destino_archivo)
                archivos_copiados.append(destino_archivo)

                cursor.execute(
                    """
                    INSERT INTO evidencias (
                        id_inspeccion,
                        ruta_archivo
                    )
                    VALUES (%s, %s)
                    """,
                    (
                        id_inspeccion,
                        destino_archivo
                    )
                )

        conexion.commit()

        messagebox.showinfo(
            "Inspección registrada",
            "La inspección fue registrada correctamente.\n\n"
            f"Estado: {estado}\n"
            f"Destino: {almacen_destino}"
        )

        limpiar_campos()

        # Actualizar la información de la inspección anterior
        # para que la ventana refleje el último registro.
        cargar_datos_llanta()

        valor_estado_anterior.set(estado_anterior_recibido)

        valor_profundidad_externa_anterior.set(
            profundidad_externa_anterior
        )

        valor_profundidad_central_anterior.set(
            profundidad_central_anterior
        )

        valor_profundidad_interna_anterior.set(
            profundidad_interna_anterior
        )

        actualizar_color_estado_anterior()

    except ValueError as error:
        if conexion is not None and conexion.is_connected():
            conexion.rollback()

        for archivo in archivos_copiados:
            try:
                if os.path.exists(archivo):
                    os.remove(archivo)
            except OSError:
                pass

        messagebox.showwarning(
            "Validación",
            str(error)
        )

    except mysql.connector.Error as error:
        if conexion is not None and conexion.is_connected():
            conexion.rollback()

        for archivo in archivos_copiados:
            try:
                if os.path.exists(archivo):
                    os.remove(archivo)
            except OSError:
                pass

        messagebox.showerror(
            "Error de base de datos",
            f"No fue posible registrar la inspección.\n\n{error}"
        )

    except Exception as error:
        if conexion is not None and conexion.is_connected():
            conexion.rollback()

        for archivo in archivos_copiados:
            try:
                if os.path.exists(archivo):
                    os.remove(archivo)
            except OSError:
                pass

        messagebox.showerror(
            "Error",
            f"Ocurrió un error inesperado.\n\n{error}"
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()


# ============================================================
# CERRAR SESIÓN
# ============================================================

def regresar_a_gestion():
    ventana.destroy()

def cerrar_sesion():
    respuesta = messagebox.askyesno(
        "Cerrar sesión",
        "¿Está seguro de que desea cerrar sesión?"
    )

    if not respuesta:
        return

    try:
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

        subprocess.Popen([
            sys.executable,
            ruta_login
        ])

        # Cerrar el módulo principal que abrió esta inspección.
        if pid_modulo_llantas:
            try:
                subprocess.Popen(
                    [
                        "taskkill",
                        "/PID",
                        str(pid_modulo_llantas),
                        "/F"
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

        ventana.destroy()

    except Exception as error:
        messagebox.showerror(
            "Error",
            f"No fue posible cerrar la sesión.\n\n{error}"
        )


# ============================================================
# VENTANA PRINCIPAL
# ============================================================

ventana = tk.Tk()

ventana.title("Nueva inspección")
ventana.geometry("900x760")
ventana.minsize(900, 760)
ventana.configure(bg=COLOR_FONDO)


# ============================================================
# ENCABEZADO
# ============================================================

encabezado = tk.Frame(
    ventana,
    bg=COLOR_AZUL_OSCURO,
    height=85
)

encabezado.pack(fill="x")
encabezado.pack_propagate(False)


boton_cerrar_sesion = tk.Button(
    encabezado,
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

boton_atras = tk.Button(
    encabezado,
    text="← Atrás",
    command=regresar_a_gestion,
    bg=COLOR_AZUL,
    fg="white",
    font=("Arial", 10, "bold"),
    relief="flat",
    padx=12,
    pady=5,
    cursor="hand2"
)
boton_atras.pack(side="left", padx=15, pady=10)



titulo = tk.Label(
    encabezado,
    text="NUEVA INSPECCION",
    font=("Arial", 22, "bold"),
    bg=COLOR_AZUL_OSCURO,
    fg=COLOR_BLANCO
)

titulo.pack(pady=(15, 2))


valor_usuario = tk.StringVar(
    value=f"{nombre_rol_recibido} {nombre_usuario_recibido}"
)

etiqueta_usuario = tk.Label(
    encabezado,
    textvariable=valor_usuario,
    font=("Arial", 11),
    bg=COLOR_AZUL_OSCURO,
    fg=COLOR_BLANCO
)

etiqueta_usuario.pack()


# ============================================================
# MARCO PRINCIPAL
# ============================================================

marco_principal = tk.Frame(
    ventana,
    bg=COLOR_FONDO
)

marco_principal.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=15
)


# ============================================================
# INFORMACIÓN DE LA LLANTA
# ============================================================

marco_llanta = tk.LabelFrame(
    marco_principal,
    text="Información de la llanta",
    font=("Arial", 9, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_AZUL_OSCURO,
    padx=15,
    pady=10
)

marco_llanta.pack(
    fill="x",
    pady=(0, 12)
)


valor_numero = tk.StringVar(value="")

valor_estado_anterior = tk.StringVar(
    value="Sin inspección previa"
)

valor_profundidad_externa_anterior = tk.StringVar(
    value="Sin dato"
)

valor_profundidad_central_anterior = tk.StringVar(
    value="Sin dato"
)

valor_profundidad_interna_anterior = tk.StringVar(
    value="Sin dato"
)


marco_informacion = tk.Frame(
    marco_llanta,
    bg=COLOR_FONDO
)

marco_informacion.pack(
    fill="x",
    pady=5
)


etiqueta_numero = tk.Label(
    marco_informacion,
    textvariable=valor_numero,
    font=("Arial", 15, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_VERDE
)

etiqueta_numero.pack(
    side="left",
    padx=(5, 15)
)


tk.Label(
    marco_informacion,
    text="|",
    font=("Arial", 13),
    bg=COLOR_FONDO,
    fg=COLOR_GRIS
).pack(side="left", padx=5)


etiqueta_estado_anterior = tk.Label(
    marco_informacion,
    textvariable=valor_estado_anterior,
    font=("Arial", 11, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_GRIS
)

etiqueta_estado_anterior.pack(
    side="left",
    padx=10
)


tk.Label(
    marco_informacion,
    text="|",
    font=("Arial", 13),
    bg=COLOR_FONDO,
    fg=COLOR_GRIS
).pack(side="left", padx=5)


tk.Label(
    marco_informacion,
    text="Ext.",
    font=("Arial", 9),
    bg=COLOR_FONDO,
    fg=COLOR_GRIS
).pack(side="left", padx=(5, 2))


tk.Label(
    marco_informacion,
    textvariable=valor_profundidad_externa_anterior,
    font=("Arial", 10, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_TEXTO
).pack(side="left", padx=(0, 8))


tk.Label(
    marco_informacion,
    text="Cent.",
    font=("Arial", 9),
    bg=COLOR_FONDO,
    fg=COLOR_GRIS
).pack(side="left", padx=(5, 2))


tk.Label(
    marco_informacion,
    textvariable=valor_profundidad_central_anterior,
    font=("Arial", 10, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_TEXTO
).pack(side="left", padx=(0, 8))


tk.Label(
    marco_informacion,
    text="Int.",
    font=("Arial", 9),
    bg=COLOR_FONDO,
    fg=COLOR_GRIS
).pack(side="left", padx=(5, 2))


tk.Label(
    marco_informacion,
    textvariable=valor_profundidad_interna_anterior,
    font=("Arial", 10, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_TEXTO
).pack(side="left", padx=(0, 5))


# ============================================================
# MARCO DE INSPECCIÓN
# ============================================================

marco_inspeccion = tk.LabelFrame(
    marco_principal,
    text="Datos de la inspección",
    font=("Arial", 11, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_AZUL_OSCURO,
    padx=15,
    pady=10
)

tk.Label(
    marco_inspeccion,
    text="Estado actual:",
    font=("Arial", 10, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_TEXTO
).grid(
    row=0,
    column=0,
    sticky="w",
    padx=(5, 10),
    pady=5
)


combo_estado = ttk.Combobox(
    marco_inspeccion,
    values=ESTADOS,
    state="readonly",
    width=22
)

combo_estado.grid(
    row=0,
    column=1,
    sticky="w",
    pady=5
)

combo_estado.bind(
    "<<ComboboxSelected>>",
    actualizar_destino_estado
)


tk.Label(
    marco_inspeccion,
    text="Destino:",
    font=("Arial", 10, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_TEXTO
).grid(
    row=0,
    column=2,
    sticky="w",
    padx=(30, 10),
    pady=5
)


combo_almacen = ttk.Combobox(
    marco_inspeccion,
    state="readonly",
    width=30
)

combo_almacen.grid(
    row=0,
    column=3,
    sticky="w",
    pady=5
)


# ============================================================
# PROFUNDIDADES
# ============================================================

marco_profundidades = tk.LabelFrame(
    marco_principal,
    text="Nuevas profundidades",
    font=("Arial", 11, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_AZUL_OSCURO,
    padx=15,
    pady=10
)

marco_profundidades.pack(
    fill="x",
    pady=(0, 12)
)


tk.Label(
    marco_profundidades,
    text="Surco Externo",
    font=("Arial", 10, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_TEXTO
).grid(row=0, column=0, padx=(5, 5), pady=5)


entrada_profundidad_externa = tk.Entry(
    marco_profundidades,
    width=6,
    font=("Arial", 10),
    justify="center"
)

entrada_profundidad_externa.grid(
    row=0,
    column=1,
    padx=(0, 20),
    pady=5
)


tk.Label(
    marco_profundidades,
    text="Surco Central",
    font=("Arial", 10, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_TEXTO
).grid(row=0, column=2, padx=(5, 5), pady=5)


entrada_profundidad_central = tk.Entry(
    marco_profundidades,
    width=6,
    font=("Arial", 10),
    justify="center"
)

entrada_profundidad_central.grid(
    row=0,
    column=3,
    padx=(0, 20),
    pady=5
)


tk.Label(
    marco_profundidades,
    text="Surco Interno",
    font=("Arial", 10, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_TEXTO
).grid(row=0, column=4, padx=(5, 5), pady=5)


entrada_profundidad_interna = tk.Entry(
    marco_profundidades,
    width=6,
    font=("Arial", 10),
    justify="center"
)

entrada_profundidad_interna.grid(
    row=0,
    column=5,
    padx=(0, 5),
    pady=5
)


entrada_profundidad_externa.bind(
    "<KeyRelease>",
    actualizar_color_profundidad
)

entrada_profundidad_central.bind(
    "<KeyRelease>",
    actualizar_color_profundidad
)

entrada_profundidad_interna.bind(
    "<KeyRelease>",
    actualizar_color_profundidad
)
# Mostrar primero las nuevas profundidades
marco_profundidades.pack(
    fill="x",
    pady=(0, 12)
)

# Mostrar después los datos de la inspección
marco_inspeccion.pack(
    fill="x",
    pady=(0, 12)
)


# ============================================================
# OBSERVACIONES
# ============================================================

marco_observaciones = tk.LabelFrame(
    marco_principal,
    text="Observaciones",
    font=("Arial", 11, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_AZUL_OSCURO,
    padx=10,
    pady=8
)

marco_observaciones.pack(
    fill="x",
    pady=(0, 12)
)


entrada_observaciones = tk.Text(
    marco_observaciones,
    height=4,
    font=("Arial", 10),
    wrap="word"
)

entrada_observaciones.pack(fill="x")


# ============================================================
# EVIDENCIAS
# ============================================================

marco_evidencias = tk.LabelFrame(
    marco_principal,
    text="Evidencias fotográficas",
    font=("Arial", 11, "bold"),
    bg=COLOR_FONDO,
    fg=COLOR_AZUL_OSCURO,
    padx=10,
    pady=8
)

marco_evidencias.pack(
    fill="x",
    pady=(0, 12)
)


boton_fotos = tk.Button(
    marco_evidencias,
    text="Seleccionar fotografías",
    command=seleccionar_fotos,
    font=("Arial", 10, "bold"),
    bg=COLOR_AZUL,
    fg=COLOR_BLANCO,
    activebackground=COLOR_AZUL_OSCURO,
    activeforeground=COLOR_BLANCO,
    relief="flat",
    padx=15,
    pady=6,
    cursor="hand2"
)

boton_fotos.pack(
    side="left",
    padx=5
)


etiqueta_fotos = tk.Label(
    marco_evidencias,
    text="Evidencias seleccionadas: 0",
    font=("Arial", 9),
    bg=COLOR_FONDO,
    fg=COLOR_GRIS
)

etiqueta_fotos.pack(
    side="left",
    padx=15
)


# ============================================================
# BOTONES
# ============================================================

marco_botones = tk.Frame(
    marco_principal,
    bg=COLOR_FONDO
)

marco_botones.pack(
    fill="x",
    pady=5
)


boton_limpiar = tk.Button(
    marco_botones,
    text="Limpiar",
    command=limpiar_campos,
    font=("Arial", 10, "bold"),
    bg=COLOR_GRIS_CLARO,
    fg=COLOR_TEXTO,
    relief="flat",
    padx=20,
    pady=8,
    cursor="hand2"
)

boton_limpiar.pack(
    side="left",
    padx=5
)


boton_registrar = tk.Button(
    marco_botones,
    text="Registrar inspección",
    command=registrar_inspeccion,
    font=("Arial", 10, "bold"),
    bg=COLOR_VERDE,
    fg=COLOR_BLANCO,
    activebackground="#1B5E20",
    activeforeground=COLOR_BLANCO,
    relief="flat",
    padx=20,
    pady=8,
    cursor="hand2"
)

boton_registrar.pack(
    side="right",
    padx=5
)


# ============================================================
# CIERRE DE VENTANA
# ============================================================

def al_cerrar_ventana():
    ventana.destroy()


ventana.protocol(
    "WM_DELETE_WINDOW",
    al_cerrar_ventana
)


# ============================================================
# CARGA INICIAL
# ============================================================

cargar_datos_llanta()

valor_estado_anterior.set(estado_anterior_recibido)

valor_profundidad_externa_anterior.set(
    profundidad_externa_anterior
)

valor_profundidad_central_anterior.set(
    profundidad_central_anterior
)

valor_profundidad_interna_anterior.set(
    profundidad_interna_anterior
)

actualizar_color_estado_anterior()

cargar_almacenes()

ventana.mainloop()
