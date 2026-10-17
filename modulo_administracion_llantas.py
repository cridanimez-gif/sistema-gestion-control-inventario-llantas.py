import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import mysql.connector
from datetime import datetime


# =========================================================
# CONFIGURACION
# =========================================================

COLOR_FONDO = "#F4F7FB"
COLOR_AZUL = "#1F4E78"
COLOR_AZUL_CLARO = "#2F75B5"
COLOR_TEXTO = "#263238"
COLOR_GRIS = "#607D8B"
COLOR_VERDE = "#2E7D32"
COLOR_ROJO = "#C62828"

DB_CONFIG = {
    "host": "localhost",
    "port": 3307,
    "user": "root",
    "password": "",
    "database": "gestion_llantas"
}

ESTADOS_ADMINISTRATIVOS = (
    "Activa",
    "Congelada",
    "Desactivada",
    "Retirada"
)


def conectar_bd():
    return mysql.connector.connect(**DB_CONFIG)


# =========================================================
# APLICACION
# =========================================================

ventana = tk.Tk()
ventana.title("Administracion de llantas")
ventana.geometry("1150x720")
ventana.minsize(950, 600)
ventana.configure(bg=COLOR_FONDO)

usuario_actual = None
ubicaciones = {}

# =========================================================
# CONSULTAS Y UBICACIONES
# =========================================================

def cargar_ubicaciones():
    conexion = conectar_bd()
    cursor = conexion.cursor()

    try:
        cursor.execute(
            "SELECT id_almacen, nombre_almacen "
            "FROM almacenes ORDER BY id_almacen"
        )

        filas = cursor.fetchall()

        ubicaciones.clear()
        for id_almacen, nombre in filas:
            ubicaciones[nombre] = id_almacen

        combo_ubicacion["values"] = list(ubicaciones.keys())

        if "Contenedor" in ubicaciones:
            combo_ubicacion.set("Contenedor")
        elif filas:
            combo_ubicacion.set(filas[0][1])

    finally:
        cursor.close()
        conexion.close()


def consultar_llantas():
    for elemento in tabla.get_children():
        tabla.delete(elemento)

    conexion = None
    cursor = None

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor()

        termino = entrada_busqueda.get().strip()

        cursor.execute(
            """
            SELECT
                l.numero_llanta,
                l.marca,
                l.diseño,
                l.dimension,
                a.nombre_almacen,
                l.situacion_administrativa,
                (
                    SELECT i.estado
                    FROM inspecciones i
                    WHERE i.numero_llanta = l.numero_llanta
                    ORDER BY i.fecha_hora_inspeccion DESC,
                             i.id_inspeccion DESC
                    LIMIT 1
                ) AS ultimo_estado
            FROM llantas l
            INNER JOIN almacenes a
                ON a.id_almacen = l.id_almacen_actual
            WHERE l.numero_llanta LIKE %s
               OR l.marca LIKE %s
            ORDER BY l.numero_llanta
            """,
            (f"%{termino}%", f"%{termino}%")
        )

        for fila in cursor.fetchall():
            tabla.insert("", "end", values=(
                fila[0],
                fila[1],
                fila[2],
                fila[3],
                fila[4],
                fila[5],
                fila[6] or "Sin inspeccion"
            ))

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Error de consulta",
            str(error)
        )

    finally:
        if cursor:
            cursor.close()
        if conexion and conexion.is_connected():
            conexion.close()


def obtener_llanta_seleccionada():
    seleccion = tabla.selection()

    if not seleccion:
        messagebox.showwarning(
            "Seleccion requerida",
            "Selecciona una llanta de la tabla."
        )
        return None

    valores = tabla.item(seleccion[0], "values")
    return valores[0]


def obtener_situacion_llanta(cursor, numero):
    cursor.execute(
        """
        SELECT
            l.situacion_administrativa,
            a.nombre_almacen,
            (
                SELECT i.estado
                FROM inspecciones i
                WHERE i.numero_llanta = l.numero_llanta
                ORDER BY i.fecha_hora_inspeccion DESC,
                         i.id_inspeccion DESC
                LIMIT 1
            ) AS ultimo_estado
        FROM llantas l
        INNER JOIN almacenes a
            ON a.id_almacen = l.id_almacen_actual
        WHERE l.numero_llanta = %s
        """,
        (numero,)
    )

    return cursor.fetchone()


# =========================================================
# REGISTRAR LLANTA NUEVA
# =========================================================

def registrar_llanta():
    numero = entrada_numero.get().strip()
    marca = entrada_marca.get().strip()
    diseno = entrada_diseno.get().strip()
    dimension = entrada_dimension.get().strip()
    dot = entrada_dot.get().strip() or None
    diseno_reencauche = (
        entrada_reencauche.get().strip() or None
    )
    ubicacion = combo_ubicacion.get()

    if not numero or not marca or not diseno or not dimension:
        messagebox.showwarning(
            "Datos incompletos",
            "Completa numero, marca, diseño y dimension."
        )
        return

    if ubicacion not in ubicaciones:
        messagebox.showwarning(
            "Ubicacion requerida",
            "Selecciona una ubicacion valida."
        )
        return

    if not messagebox.askyesno(
        "Confirmar registro",
        f"¿Deseas registrar la llanta {numero}?"
    ):
        return

    conexion = None
    cursor = None

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor()

        cursor.execute(
            """
            INSERT INTO llantas (
                numero_llanta,
                marca,
                diseño,
                diseño_reencauche,
                dimension,
                dot,
                id_almacen_actual
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                numero,
                marca,
                diseno,
                diseno_reencauche,
                dimension,
                dot,
                ubicaciones[ubicacion]
            )
        )

        conexion.commit()

        messagebox.showinfo(
            "Registro exitoso",
            "La llanta fue registrada correctamente."
        )

        for campo in (
            entrada_numero,
            entrada_marca,
            entrada_diseno,
            entrada_dimension,
            entrada_dot,
            entrada_reencauche
        ):
            campo.delete(0, tk.END)

        consultar_llantas()

    except mysql.connector.IntegrityError:
        if conexion:
            conexion.rollback()

        messagebox.showwarning(
            "Llanta existente",
            "Ya existe una llanta con ese numero."
        )

    except mysql.connector.Error as error:
        if conexion:
            conexion.rollback()

        messagebox.showerror(
            "Error al registrar",
            str(error)
        )

    finally:
        if cursor:
            cursor.close()
        if conexion and conexion.is_connected():
            conexion.close()


# =========================================================
# HISTORIAL DE INSPECCIONES
# =========================================================

def consultar_historial():
    numero = obtener_llanta_seleccionada()

    if not numero:
        return

    conexion = None
    cursor = None

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor()

        cursor.execute(
            """
            SELECT
                i.id_inspeccion,
                i.fecha_hora_inspeccion,
                u.nombre,
                u.apellido,
                i.estado,
                i.profundidad_externa,
                i.profundidad_central,
                i.profundidad_interna,
                i.observaciones,
                a.nombre_almacen
            FROM inspecciones i
            INNER JOIN usuarios u
                ON u.id_usuario = i.id_usuario
            INNER JOIN almacenes a
                ON a.id_almacen = i.id_almacen_destino
            WHERE i.numero_llanta = %s
            ORDER BY i.fecha_hora_inspeccion DESC,
                     i.id_inspeccion DESC
            """,
            (numero,)
        )

        inspecciones = cursor.fetchall()

        if not inspecciones:
            messagebox.showinfo(
                "Historial",
                "Esta llanta aun no tiene inspecciones."
            )
            return

        detalle = []

        for fila in inspecciones:
            cursor.execute(
                """
                SELECT ruta_archivo
                FROM evidencias
                WHERE id_inspeccion = %s
                """,
                (fila[0],)
            )
            evidencias = cursor.fetchall()

            detalle.append(
                f"Inspeccion #{fila[0]}\n"
                f"Fecha: {fila[1]}\n"
                f"Responsable: {fila[2]} {fila[3]}\n"
                f"Estado: {fila[4]}\n"
                f"Profundidades externa/central/interna: "
                f"{fila[5]} / {fila[6]} / {fila[7]}\n"
                f"Observaciones: {fila[8] or 'Sin observaciones'}\n"
                f"Ubicacion destino: {fila[9]}\n"
                f"Evidencias registradas: {len(evidencias)}\n"
                + "\n".join(
                    f"  - {e[0]}" for e in evidencias
                )
            )

        ventana_historial = tk.Toplevel(ventana)
        ventana_historial.title(
            f"Historial de la llanta {numero}"
        )
        ventana_historial.geometry("780x560")
        ventana_historial.configure(bg=COLOR_FONDO)

        tk.Label(
            ventana_historial,
            text=f"Historial de inspecciones: {numero}",
            font=("Arial", 14, "bold"),
            bg=COLOR_FONDO,
            fg=COLOR_AZUL
        ).pack(pady=10)

        area = tk.Text(
            ventana_historial,
            wrap="word",
            font=("Arial", 10)
        )
        area.pack(fill="both", expand=True, padx=12, pady=8)
        area.insert("1.0", "\n\n".join(detalle))
        area.config(state="disabled")

    except mysql.connector.Error as error:
        messagebox.showerror(
            "Error de historial",
            str(error)
        )

    finally:
        if cursor:
            cursor.close()
        if conexion and conexion.is_connected():
            conexion.close()


# =========================================================
# CONGELAR, REACTIVAR Y DESACTIVAR
# =========================================================

def cambiar_situacion(nueva_situacion):
    numero = obtener_llanta_seleccionada()

    if not numero:
        return

    conexion = None
    cursor = None

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor()

        situacion = obtener_situacion_llanta(cursor, numero)

        if not situacion:
            messagebox.showerror(
                "Error",
                "No se encontro la llanta."
            )
            return

        actual, ubicacion, estado = situacion

        if actual == "Retirada":
            messagebox.showwarning(
                "Operacion no permitida",
                "La llanta ya fue retirada fisicamente."
            )
            return

        if nueva_situacion == "Congelada":
            if actual != "Activa":
                messagebox.showwarning(
                    "Operacion no permitida",
                    "Solo se pueden congelar llantas activas."
                )
                return

        elif nueva_situacion == "Activa":
            if actual != "Congelada":
                messagebox.showwarning(
                    "Operacion no permitida",
                    "Solo se pueden reactivar llantas congeladas."
                )
                return

        elif nueva_situacion == "Desactivada":
            if ubicacion != "Pila de Desecho" or estado != "Desecho":
                messagebox.showwarning(
                    "Operacion no permitida",
                    "Solo se puede desactivar una llanta "
                    "ubicada en Pila de Desecho y cuyo ultimo "
                    "estado de inspeccion sea Desecho."
                )
                return

            if actual not in ("Activa", "Congelada"):
                messagebox.showwarning(
                    "Operacion no permitida",
                    "La llanta no esta en una situacion "
                    "que permita desactivarla."
                )
                return

        if not messagebox.askyesno(
            "Confirmar cambio",
            f"¿Cambiar la situacion de {numero} "
            f"a {nueva_situacion}?"
        ):
            return

        cursor.execute(
            """
            UPDATE llantas
            SET situacion_administrativa = %s
            WHERE numero_llanta = %s
            """,
            (nueva_situacion, numero)
        )

        conexion.commit()

        messagebox.showinfo(
            "Operacion exitosa",
            f"La llanta ahora figura como {nueva_situacion}."
        )

        consultar_llantas()

    except mysql.connector.Error as error:
        if conexion:
            conexion.rollback()

        messagebox.showerror(
            "Error al actualizar",
            str(error)
        )

    finally:
        if cursor:
            cursor.close()
        if conexion and conexion.is_connected():
            conexion.close()


# =========================================================
# REGISTRAR RETIRO FISICO
# =========================================================

def registrar_retiro_fisico():
    numero = obtener_llanta_seleccionada()

    if not numero:
        return

    conexion = None
    cursor = None

    try:
        conexion = conectar_bd()
        cursor = conexion.cursor()

        situacion = obtener_situacion_llanta(cursor, numero)

        if not situacion:
            messagebox.showerror(
                "Error",
                "No se encontro la llanta."
            )
            return

        actual, ubicacion, estado = situacion

        if actual == "Retirada":
            messagebox.showinfo(
                "Retiro registrado",
                "Esta llanta ya figura como retirada."
            )
            return

        if ubicacion != "Pila de Desecho" or estado != "Desecho":
            messagebox.showwarning(
                "Retiro no permitido",
                "La llanta debe estar en Pila de Desecho "
                "y su ultima inspeccion debe indicar Desecho."
            )
            return

        empresa = simpledialog.askstring(
            "Empresa externa",
            "Nombre de la empresa que retira la llanta:",
            parent=ventana
        )

        if empresa is None:
            return

        empresa = empresa.strip()

        if not empresa:
            messagebox.showwarning(
                "Dato requerido",
                "Debes indicar la empresa que retira la llanta."
            )
            return

        confirmar = messagebox.askyesno(
            "Confirmar retiro fisico",
            f"¿Confirmas que la empresa {empresa} "
            f"ya retiro fisicamente la llanta {numero}?"
        )

        if not confirmar:
            return

        cursor.execute(
            """
            UPDATE llantas
            SET situacion_administrativa = 'Retirada',
                fecha_retiro_fisico = %s,
                empresa_retiro = %s
            WHERE numero_llanta = %s
            """,
            (datetime.now(), empresa, numero)
        )

        conexion.commit()

        messagebox.showinfo(
            "Retiro registrado",
            "Se registro el retiro fisico.\n"
            "El historial de inspecciones y evidencias "
            "se conserva."
        )

        consultar_llantas()

    except mysql.connector.Error as error:
        if conexion:
            conexion.rollback()

        messagebox.showerror(
            "Error al registrar retiro",
            str(error)
        )

    finally:
        if cursor:
            cursor.close()
        if conexion and conexion.is_connected():
            conexion.close()


# =========================================================
# INTERFAZ PRINCIPAL
# =========================================================

def mostrar_aplicacion():
    for widget in ventana.winfo_children():
        widget.destroy()

    ventana.title("Administracion de llantas")
    ventana.geometry("1150x720")

    encabezado = tk.Frame(ventana, bg=COLOR_AZUL)
    encabezado.pack(fill="x")

    tk.Label(
        encabezado,
        text="ADMINISTRACION DE LLANTAS",
        font=("Arial", 17, "bold"),
        bg=COLOR_AZUL,
        fg="white"
    ).pack(side="left", padx=18, pady=14)

    tk.Label(
        encabezado,
        text=(
            f"{usuario_actual['nombre']} "
            f"{usuario_actual['apellido']} | "
            f"{usuario_actual['nombre_rol']}"
        ),
        font=("Arial", 10),
        bg=COLOR_AZUL,
        fg="white"
    ).pack(side="right", padx=18)
    
    tk.Button(
        encabezado,
        text="Volver atrás",
        command=ventana.destroy,
        bg=COLOR_AZUL_CLARO,
        fg="white",
        relief="flat",
        cursor="hand2"
    ).pack(side="right", padx=5, pady=8)

    tk.Button(
        encabezado,
        text="Cerrar sesión",
        command=ventana.destroy,
        bg=COLOR_ROJO,
        fg="white",
        relief="flat",
        cursor="hand2"
    ).pack(side="right", padx=5, pady=8)


    marco_registro = tk.LabelFrame(
        ventana,
        text="Registrar llanta nueva",
        bg=COLOR_FONDO,
        fg=COLOR_AZUL,
        font=("Arial", 11, "bold"),
        padx=10,
        pady=8
    )
    marco_registro.pack(fill="x", padx=12, pady=8)

    global entrada_numero, entrada_marca, entrada_diseno
    global entrada_dimension, entrada_dot, entrada_reencauche
    global combo_ubicacion

    def crear_campo(parent, texto, fila, columna):
        tk.Label(
            parent,
            text=texto,
            bg=COLOR_FONDO,
            fg=COLOR_TEXTO
        ).grid(
            row=fila, column=columna,
            sticky="w", padx=5, pady=4
        )

        campo = ttk.Entry(parent, width=22)
        campo.grid(
            row=fila, column=columna + 1,
            sticky="ew", padx=5, pady=4
        )
        return campo

    entrada_numero = crear_campo(
        marco_registro, "Numero:", 0, 0
    )
    entrada_marca = crear_campo(
        marco_registro, "Marca:", 0, 2
    )
    entrada_diseno = crear_campo(
        marco_registro, "Diseño:", 0, 4
    )
    entrada_dimension = crear_campo(
        marco_registro, "Dimension:", 1, 0
    )
    entrada_dot = crear_campo(
        marco_registro, "DOT:", 1, 2
    )
    entrada_reencauche = crear_campo(
        marco_registro, "Diseño reencauche:", 1, 4
    )

    tk.Label(
        marco_registro,
        text="Ubicacion inicial:",
        bg=COLOR_FONDO
    ).grid(row=2, column=0, sticky="w", padx=5, pady=4)

    combo_ubicacion = ttk.Combobox(
        marco_registro,
        width=20,
        state="readonly"
    )
    combo_ubicacion.grid(
        row=2, column=1, sticky="ew", padx=5, pady=4
    )

    tk.Button(
        marco_registro,
        text="Registrar llanta",
        command=registrar_llanta,
        bg=COLOR_VERDE,
        fg="white",
        font=("Arial", 10, "bold"),
        relief="flat",
        padx=10,
        pady=6
    ).grid(row=2, column=2, padx=5, pady=4)

    marco_consulta = tk.Frame(ventana, bg=COLOR_FONDO)
    marco_consulta.pack(fill="x", padx=12, pady=5)

    tk.Label(
        marco_consulta,
        text="Buscar por numero o marca:",
        bg=COLOR_FONDO,
        fg=COLOR_TEXTO
    ).pack(side="left", padx=5)

    global entrada_busqueda
    entrada_busqueda = ttk.Entry(marco_consulta, width=30)
    entrada_busqueda.pack(side="left", padx=5)

    tk.Button(
        marco_consulta,
        text="Consultar",
        command=consultar_llantas,
        bg=COLOR_AZUL_CLARO,
        fg="white",
        relief="flat"
    ).pack(side="left", padx=5)

    columnas = (
        "numero", "marca", "diseno", "dimension",
        "ubicacion", "situacion", "estado"
    )

    global tabla
    marco_tabla = tk.Frame(ventana)
    marco_tabla.pack(fill="both", expand=True, padx=12, pady=5)

    tabla = ttk.Treeview(
        marco_tabla,
        columns=columnas,
        show="headings",
        height=12
    )

    encabezados = {
        "numero": "Numero",
        "marca": "Marca",
        "diseno": "Diseño",
        "dimension": "Dimension",
        "ubicacion": "Ubicacion",
        "situacion": "Situacion administrativa",
        "estado": "Ultimo estado"
    }

    anchos = {
        "numero": 110,
        "marca": 120,
        "diseno": 130,
        "dimension": 100,
        "ubicacion": 180,
        "situacion": 155,
        "estado": 110
    }

    for columna in columnas:
        tabla.heading(columna, text=encabezados[columna])
        tabla.column(
            columna,
            width=anchos[columna],
            anchor="center"
        )

    barra = ttk.Scrollbar(
        marco_tabla,
        orient="vertical",
        command=tabla.yview
    )
    tabla.configure(yscrollcommand=barra.set)

    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")

    marco_acciones = tk.Frame(ventana, bg=COLOR_FONDO)
    marco_acciones.pack(fill="x", padx=12, pady=10)

    acciones = [
        ("Ver historial", consultar_historial, COLOR_AZUL),
        ("Congelar", lambda: cambiar_situacion("Congelada"),
         COLOR_GRIS),
        ("Reactivar", lambda: cambiar_situacion("Activa"),
         COLOR_VERDE),
        ("Desactivar", lambda: cambiar_situacion("Desactivada"),
         COLOR_ROJO),
        ("Registrar retiro fisico", registrar_retiro_fisico,
         COLOR_AZUL_CLARO)
    ]

    for texto, comando, color in acciones:
        tk.Button(
            marco_acciones,
            text=texto,
            command=comando,
            bg=color,
            fg="white",
            font=("Arial", 9, "bold"),
            relief="flat",
            padx=9,
            pady=7
        ).pack(side="left", padx=4)

    cargar_ubicaciones()
    consultar_llantas()


# =========================================================
# INICIAR EL MÓDULO CON LA SESIÓN EXISTENTE
# =========================================================

if len(sys.argv) >= 5:
    try:
        id_usuario = int(sys.argv[1])
        nombre_usuario = sys.argv[2]
        id_rol = int(sys.argv[3])
        nombre_rol = sys.argv[4]

        if id_rol not in (2, 3):
            messagebox.showerror(
                "Acceso restringido",
                "Solo Analista e Ingeniero pueden ingresar."
            )
            ventana.destroy()
        else:
            usuario_actual = {
                "id": id_usuario,
                "nombre": nombre_usuario,
                "apellido": "",
                "rol": id_rol,
                "nombre_rol": nombre_rol
            }

            mostrar_aplicacion()

    except (ValueError, TypeError) as error:
        messagebox.showerror(
            "Error de sesión",
            f"No se pudieron validar los datos del usuario.\n{error}"
        )
        ventana.destroy()
else:
    messagebox.showerror(
        "Sesión no recibida",
        "Abre este módulo desde gestion_llantas.py."
    )
    ventana.destroy()

ventana.mainloop()

