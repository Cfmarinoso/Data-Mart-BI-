"""
DATAMART AUTOCONSTRUCCION (encuestas de censadores) -> SQL Server
Sigue la plantilla del datamart Northwind: conexion con pyodbc, crear esquema (borra y crea),
cargar dimensiones, cargar tabla de hechos.

Origen  : data_origen_1.xlsx  (+ oficinas.csv y peru_distrital_simple.geojson, opcionales, solo para nombres)
Destino : SQL Server, base DatamartAutoconstruccion (el script la crea si no existe)
Grano   : 1 fila de fact_consumo = 1 encuesta de censador (codencuestacensadores)

Uso:
    python codigo_completo_datamart_autoconstruccion.py              # carga completa
    python codigo_completo_datamart_autoconstruccion.py --dry-run    # solo prepara y valida en memoria, no toca SQL Server

Requiere: pip install pyodbc pandas openpyxl     (y ODBC Driver 17 for SQL Server)
"""
import os
import sys
import json
import datetime as dt

import numpy as np
import pandas as pd
import pyodbc

# ----------------------------------------------------------------------------- CONFIGURACION
RUTA_DATOS = "data_origen_1.xlsx"
RUTA_OFICINAS = "oficinas.csv"                     # opcional: nombres de oficina
RUTA_GEOJSON = "peru_distrital_simple.geojson"     # opcional: nombres de departamento/provincia/distrito

SERVER = os.getenv("SQL_SERVER", "localhost")
DATABASE = "DatamartAutoconstruccion"
UID = os.getenv("SQL_UID", "sa")
PWD = os.getenv("SQL_PWD", "1234567890")           # recomendado: definir SQL_PWD como variable de entorno

FECHA_INI = dt.date(2023, 1, 1)                    # rango de la dimension Tiempo
FECHA_FIN = dt.date(2031, 12, 31)

# codigomarcalocal que se considera MARCA PROPIA (1 = "Cemex Cemento", antes "Pacasmayo Cemento").
# Si Pacasmayo Concreto (15), Rapimix (28), Bloques/Adoquines Pacasmayo (23, 25) tambien son propias, agregarlas aqui.
MARCAS_PROPIAS = {1}

SIN_DESC = "SIN DESCRIPCION"
LOTE = 20000                                       # filas por executemany

# columnas del origen que NO se cargan
DESCARTAR = ["Unnamed: 0", "desobservacionom_encuesta", "fecha_creacion_visita"]

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Setiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]


# ----------------------------------------------------------------------------- CONEXIONES
def _cadena(database):
    return (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={SERVER};DATABASE={database};UID={UID};PWD={PWD}"
    )


def crear_base_si_no_existe():
    try:
        conn = pyodbc.connect(_cadena("master"), autocommit=True)   # CREATE DATABASE no corre dentro de una transaccion
        conn.cursor().execute(f"IF DB_ID(N'{DATABASE}') IS NULL CREATE DATABASE [{DATABASE}]")
        conn.close()
        return True
    except pyodbc.Error as e:
        print(f"Error al crear/verificar la base: {e}")
        return False


def get_connection_destino():
    try:
        conn = pyodbc.connect(_cadena(DATABASE))
        print("✓ Conexión a destino exitosa")
        return conn
    except pyodbc.Error as e:
        print(f"Error de conexión al destino: {e}")
        return None


# ----------------------------------------------------------------------------- ESQUEMA
# Orden de borrado: primero el hecho, luego las dimensiones
TABLAS = ["fact_consumo", "Competencia", "Proveedor", "Ejecutivo", "Motivo", "UnidadMedida",
          "Marca", "TipoEstructura", "Obra", "Ubigeo", "Oficina", "Tiempo"]

DDL = [
    """CREATE TABLE Tiempo (
        id INT NOT NULL PRIMARY KEY,                 -- yyyymmdd (igual a iddia del origen)
        fecha DATE NOT NULL UNIQUE,
        anio SMALLINT NOT NULL,
        trimestre TINYINT NOT NULL,
        numMes TINYINT NOT NULL,
        mes NVARCHAR(12) NOT NULL,
        anioMes INT NOT NULL,                        -- yyyymm
        dia TINYINT NOT NULL,
        semanaISO TINYINT NOT NULL,
        diaSemana TINYINT NOT NULL,                  -- 1 = lunes ... 7 = domingo
        nombreDia NVARCHAR(12) NOT NULL,
        esFinDeSemana BIT NOT NULL
    )""",
    """CREATE TABLE Oficina (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo INT NOT NULL UNIQUE,                  -- idoficina
        nombre NVARCHAR(100) NOT NULL,
        idSociedad INT NULL
    )""",
    """CREATE TABLE Ubigeo (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo CHAR(6) NOT NULL UNIQUE,              -- ubigeo INEI: dep(2) + prov(2) + dist(2)
        codDepartamento INT NOT NULL,
        codProvincia INT NOT NULL,
        codDistrito INT NOT NULL,
        departamento NVARCHAR(100) NOT NULL,
        provincia NVARCHAR(100) NOT NULL,
        distrito NVARCHAR(100) NOT NULL
    )""",
    """CREATE TABLE Obra (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo BIGINT NOT NULL UNIQUE,               -- codigoobra (supera el rango de INT)
        idMaestroObra INT NULL,                      -- una obra llega a tener varios: se toma el de la encuesta mas reciente
        tipoEjecucion NVARCHAR(50) NOT NULL
    )""",
    """CREATE TABLE TipoEstructura (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo INT NOT NULL UNIQUE,                  -- id_tipo_estructura
        nombre NVARCHAR(100) NOT NULL
    )""",
    # Marca: una fila por codigotipomarcalocal (determina marca, linea, sublinea y producto)
    """CREATE TABLE Marca (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo INT NOT NULL UNIQUE,                  -- codigotipomarcalocal
        tipoMarca NVARCHAR(100) NOT NULL,            -- destipomarca (NO usar para analizar marcas)
        codMarca INT NULL,
        marca NVARCHAR(100) NOT NULL,                -- desmarca tal como llega
        marcaNormalizada NVARCHAR(100) NOT NULL,     -- UPPER(desmarca): une 'Holcim' y 'HOLCIM'
        esMarcaPropia BIT NOT NULL,
        codLinea INT NULL,
        linea NVARCHAR(100) NOT NULL,
        codSublinea INT NULL,
        sublinea NVARCHAR(100) NOT NULL,
        codProducto INT NULL,
        producto NVARCHAR(100) NOT NULL
    )""",
    """CREATE TABLE UnidadMedida (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo INT NOT NULL UNIQUE,
        abreviatura NVARCHAR(20) NOT NULL
    )""",
    """CREATE TABLE Motivo (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo INT NOT NULL UNIQUE,
        nombre NVARCHAR(100) NOT NULL                -- el codigo 12 llega sin descripcion
    )""",
    """CREATE TABLE Ejecutivo (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo INT NOT NULL UNIQUE,                  -- codcreadorom (1:1 con ejecutivosapvisita)
        ejecutivoSAP INT NULL,
        nombre NVARCHAR(150) NOT NULL
    )""",
    """CREATE TABLE Proveedor (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo BIGINT NOT NULL UNIQUE,               -- codisicom_isicom_proveedor (12 digitos)
        nombre NVARCHAR(200) NOT NULL                -- no viene en el dataset: completar desde comercial_lcm_cliente_isicom
    )""",
    """CREATE TABLE Competencia (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codTipoCompetencia INT NOT NULL,             -- 0 = no aplica
        tipoCompetencia NVARCHAR(100) NOT NULL,
        codMarcaCemento INT NOT NULL,                -- 0 = no aplica
        marcaCemento NVARCHAR(100) NOT NULL,
        CONSTRAINT UQ_Competencia UNIQUE (codTipoCompetencia, codMarcaCemento)
    )""",
    """CREATE TABLE fact_consumo (
        id INT NOT NULL PRIMARY KEY,                 -- codencuestacensadores
        visitaID INT NOT NULL,                       -- codvisita (dimension degenerada)
        tiempoID INT NOT NULL,
        oficinaID INT NOT NULL,
        ubigeoID INT NOT NULL,
        obraID INT NOT NULL,
        tipoEstructuraID INT NOT NULL,
        marcaID INT NOT NULL,
        unidadMedidaID INT NOT NULL,
        motivoID INT NOT NULL,
        ejecutivoID INT NOT NULL,
        proveedorID INT NOT NULL,
        competenciaID INT NOT NULL,
        idSociedad SMALLINT NOT NULL,
        sociedadCli6052 BIT NOT NULL,
        sociedadCli6012 BIT NOT NULL,
        tipoVisita TINYINT NOT NULL,                 -- 1 / 2 (significado por confirmar con negocio)
        estado BIT NOT NULL,
        posibilidadReversion BIT NOT NULL,
        flagMotivoCpsaa BIT NOT NULL,
        volumen DECIMAL(18,2) NOT NULL,
        volumenRestante DECIMAL(18,2) NOT NULL,
        precio DECIMAL(18,2) NOT NULL,
        fechaIngreso DATE NULL,
        fechaCreacion DATETIME2(3) NOT NULL,
        fechaModificacion DATETIME2(3) NULL,
        checkin DATETIME2(0) NULL,
        checkout DATETIME2(0) NULL,
        duracionMin AS (CASE WHEN checkout >= checkin THEN DATEDIFF(MINUTE, checkin, checkout) END) PERSISTED,
        checkinLatitud DECIMAL(10,7) NULL,
        checkinLongitud DECIMAL(10,7) NULL,
        checkoutLatitud DECIMAL(10,7) NULL,
        checkoutLongitud DECIMAL(10,7) NULL,
        acciones NVARCHAR(500) NULL,
        observacion NVARCHAR(500) NULL,
        FOREIGN KEY (tiempoID) REFERENCES Tiempo(id),
        FOREIGN KEY (oficinaID) REFERENCES Oficina(id),
        FOREIGN KEY (ubigeoID) REFERENCES Ubigeo(id),
        FOREIGN KEY (obraID) REFERENCES Obra(id),
        FOREIGN KEY (tipoEstructuraID) REFERENCES TipoEstructura(id),
        FOREIGN KEY (marcaID) REFERENCES Marca(id),
        FOREIGN KEY (unidadMedidaID) REFERENCES UnidadMedida(id),
        FOREIGN KEY (motivoID) REFERENCES Motivo(id),
        FOREIGN KEY (ejecutivoID) REFERENCES Ejecutivo(id),
        FOREIGN KEY (proveedorID) REFERENCES Proveedor(id),
        FOREIGN KEY (competenciaID) REFERENCES Competencia(id)
    )""",
]

# Miembro "DESCONOCIDO" (id = -1) de cada dimension: las filas sin llave caen aqui en vez de perderse.
DESCONOCIDOS = {
    "Oficina": "(id, codigo, nombre, idSociedad) VALUES (-1, -1, N'DESCONOCIDO', NULL)",
    "Ubigeo": "(id, codigo, codDepartamento, codProvincia, codDistrito, departamento, provincia, distrito) "
              "VALUES (-1, '000000', 0, 0, 0, N'DESCONOCIDO', N'DESCONOCIDO', N'DESCONOCIDO')",
    "Obra": "(id, codigo, idMaestroObra, tipoEjecucion) VALUES (-1, -1, NULL, N'DESCONOCIDO')",
    "TipoEstructura": "(id, codigo, nombre) VALUES (-1, -1, N'DESCONOCIDO')",
    "Marca": "(id, codigo, tipoMarca, codMarca, marca, marcaNormalizada, esMarcaPropia, codLinea, linea, "
             "codSublinea, sublinea, codProducto, producto) VALUES (-1, -1, N'DESCONOCIDO', NULL, N'DESCONOCIDO', "
             "N'DESCONOCIDO', 0, NULL, N'DESCONOCIDO', NULL, N'DESCONOCIDO', NULL, N'DESCONOCIDO')",
    "UnidadMedida": "(id, codigo, abreviatura) VALUES (-1, -1, N'DESCONOCIDO')",
    "Motivo": "(id, codigo, nombre) VALUES (-1, -1, N'DESCONOCIDO')",
    "Ejecutivo": "(id, codigo, ejecutivoSAP, nombre) VALUES (-1, -1, NULL, N'DESCONOCIDO')",
    "Proveedor": "(id, codigo, nombre) VALUES (-1, -1, N'DESCONOCIDO')",
    # Competencia: -1 = "NO APLICA" (0/0), el caso mas comun (~89% de las filas)
    "Competencia": "(id, codTipoCompetencia, tipoCompetencia, codMarcaCemento, marcaCemento) "
                   "VALUES (-1, 0, N'NO APLICA', 0, N'NO APLICA')",
}

INDICES = [
    "CREATE INDEX IX_fact_consumo_tiempo ON fact_consumo (tiempoID)",
    "CREATE INDEX IX_fact_consumo_obra ON fact_consumo (obraID)",
    "CREATE INDEX IX_fact_consumo_oficina ON fact_consumo (oficinaID)",
    "CREATE INDEX IX_fact_consumo_ubigeo ON fact_consumo (ubigeoID)",
    "CREATE INDEX IX_fact_consumo_marca ON fact_consumo (marcaID)",
    "CREATE INDEX IX_fact_consumo_visita ON fact_consumo (visitaID)",
]


# Vista plana (hechos + dimensiones) para que cualquier usuario consulte sin escribir JOINs.
# La usan el dashboard y la pestaña "Consultas SQL".
VISTA = """CREATE VIEW vw_consumo AS
    SELECT e.id AS id_encuesta, e.visitaID AS id_visita, ob.codigo AS id_obra, t.fecha, t.anio,
           CONCAT(t.anio, '-', RIGHT('0' + CAST(t.numMes AS VARCHAR(2)), 2)) AS mes,
           ofi.nombre AS oficina, u.codigo AS ubigeo, u.departamento, u.provincia, u.distrito,
           te.nombre AS tipo_estructura, ob.tipoEjecucion AS tipo_ejecucion,
           m.marca, m.marcaNormalizada AS marca_norm, m.esMarcaPropia AS es_propia,
           m.producto, m.linea, m.sublinea, um.abreviatura AS unidad,
           mo.nombre AS motivo, ej.nombre AS ejecutivo, pr.codigo AS proveedor_codigo,
           co.tipoCompetencia AS tipo_competencia, co.marcaCemento AS marca_competencia,
           e.volumen, e.volumenRestante AS volumen_restante, e.precio,
           e.tipoVisita AS tipo_visita, e.estado,
           e.checkinLatitud AS lat, e.checkinLongitud AS lon
    FROM fact_consumo e
    JOIN Tiempo         t   ON e.tiempoID         = t.id
    JOIN Oficina        ofi ON e.oficinaID        = ofi.id
    JOIN Ubigeo         u   ON e.ubigeoID         = u.id
    JOIN Obra           ob  ON e.obraID           = ob.id
    JOIN TipoEstructura te  ON e.tipoEstructuraID = te.id
    JOIN Marca          m   ON e.marcaID          = m.id
    JOIN UnidadMedida   um  ON e.unidadMedidaID   = um.id
    JOIN Motivo         mo  ON e.motivoID         = mo.id
    JOIN Ejecutivo      ej  ON e.ejecutivoID      = ej.id
    JOIN Proveedor      pr  ON e.proveedorID      = pr.id
    JOIN Competencia    co  ON e.competenciaID    = co.id"""


def create_datamart_schema(cursor):
    # Borra hechos primero y luego dimensiones; asi los cambios de esquema siempre se aplican
    cursor.execute("IF OBJECT_ID('vw_consumo', 'V') IS NOT NULL DROP VIEW vw_consumo")
    for t in TABLAS:
        cursor.execute(f"IF OBJECT_ID('{t}', 'U') IS NOT NULL DROP TABLE {t}")
    for sentencia in DDL:
        cursor.execute(sentencia)
    for tabla, valores in DESCONOCIDOS.items():
        cursor.execute(f"SET IDENTITY_INSERT {tabla} ON; INSERT INTO {tabla} {valores}; SET IDENTITY_INSERT {tabla} OFF;")
    cursor.execute(VISTA)
    cursor.commit()


# ----------------------------------------------------------------------------- LECTURA Y LIMPIEZA DEL ORIGEN
def leer_origen():
    print(f"Leyendo {RUTA_DATOS} ...")
    if RUTA_DATOS.lower().endswith(".csv"):
        return pd.read_csv(RUTA_DATOS, low_memory=False)
    return pd.read_excel(RUTA_DATOS, engine="openpyxl")


def preparar_origen(raw):
    df = raw.drop(columns=[c for c in DESCARTAR if c in raw.columns]).copy()

    enteros = ["iddia", "codcreadorom", "codencuestacensadores", "codigotipomarcalocal", "codvisita",
               "codigoobra", "idoficina", "cod_departamento", "cod_provincia", "cod_distrito", "idsociedad",
               "id_maestro_obra", "id_tipo_estructura", "codigomarcalocal", "codunidadmedidaisicom", "codlinea",
               "codsublinea", "codproducto", "codtipocompetencia_concreto", "codmotivoom", "ejecutivosapvisita",
               "codisicom_isicom_proveedor", "codisicommarcacemento", "tipo_de_visita"]
    for c in enteros:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    for c in ["fecha_ingreso_encuesta", "fecha_creacion_encuesta", "fecha_modificacion", "checkin", "checkout"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")

    for c in ["posibilidadreversion_cen", "flagmotivocpsaa", "estado"]:
        df[c] = df[c].astype("boolean").fillna(False).astype(bool)
    for c in ["sociedad_cli_6052", "sociedad_cli_6012"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).ne(0)

    for c in ["volumencensadoresencuesta", "volumenrestantecensadoresencuesta", "preciocensadoresencuesta"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).round(2)

    textos = ["desaccionesom", "desobservacionom", "tipoejecucion_cen", "tipoestructura_cen", "destipomarca",
              "desmarca", "abrevunidadmedidaisicom", "deslinea", "dessublinea", "desproducto",
              "destipocompetencia_concreto", "desmotivoom", "descreadorom", "desisicommarcacemento"]
    for c in textos:
        df[c] = df[c].astype("string").str.strip().replace("", pd.NA)

    # Coordenadas: (0,0) no existe en Peru -> NULL (check-in y check-out por separado)
    for pref in ["checkin", "checkout"]:
        la, lo = f"{pref}_latitud", f"{pref}_longitud"
        malo = (df[la].fillna(0) == 0) & (df[lo].fillna(0) == 0)
        df[la] = df[la].mask(malo)
        df[lo] = df[lo].mask(malo)

    # Ubigeo de 6 digitos (dep + prov + dist). OJO: el codigo de distrito solo no es unico.
    df["ubigeo"] = ((df["cod_departamento"] * 10000 + df["cod_provincia"] * 100 + df["cod_distrito"])
                    .astype("Int64").astype(str).str.zfill(6))

    # Competencia: 0 = no aplica
    df["comp_tipo"] = df["codtipocompetencia_concreto"].fillna(0)
    df["comp_marca"] = df["codisicommarcacemento"].fillna(0)

    if df["codencuestacensadores"].duplicated().any():
        raise ValueError("Hay codencuestacensadores duplicados en el origen.")
    return df


def leer_nombres_oficina():
    if not os.path.exists(RUTA_OFICINAS):
        print(f"(sin {RUTA_OFICINAS}: las oficinas quedan como '{SIN_DESC}')")
        return pd.DataFrame(columns=["codigo", "nombre"])
    o = pd.read_csv(RUTA_OFICINAS)
    return o.rename(columns={"idoficina": "codigo", "desoficina": "nombre"})[["codigo", "nombre"]].drop_duplicates("codigo")


def leer_nombres_ubigeo():
    if not os.path.exists(RUTA_GEOJSON):
        print(f"(sin {RUTA_GEOJSON}: departamento/provincia/distrito quedan como '{SIN_DESC}')")
        return pd.DataFrame(columns=["codigo", "departamento", "provincia", "distrito"])
    with open(RUTA_GEOJSON, encoding="utf-8") as f:
        props = [x["properties"] for x in json.load(f)["features"]]
    g = pd.DataFrame(props).rename(columns={"IDDIST": "codigo", "NOMBDEP": "departamento",
                                             "NOMBPROV": "provincia", "NOMBDIST": "distrito"})
    return g[["codigo", "departamento", "provincia", "distrito"]].drop_duplicates("codigo")


# ----------------------------------------------------------------------------- CONSTRUCCION DE DIMENSIONES (en memoria)
def primero(df, clave, cols, ordenar_desc=None):
    """Una fila por clave; para cada columna toma el primer valor NO nulo (si una fila llega vacia, se usa la que si trae dato)."""
    d = df.dropna(subset=[clave] if isinstance(clave, str) else clave)
    if ordenar_desc:
        d = d.sort_values(ordenar_desc, ascending=False)
    return d.groupby(clave, as_index=False, sort=True)[cols].first()


def rellenar(s):
    return s.astype("string").fillna(SIN_DESC)


def construir_dimensiones(df):
    dims = {}

    # Tiempo: calendario completo
    f = pd.date_range(FECHA_INI, FECHA_FIN, freq="D")
    t = pd.DataFrame({"fecha": f})
    t["id"] = t.fecha.dt.year * 10000 + t.fecha.dt.month * 100 + t.fecha.dt.day
    t["anio"] = t.fecha.dt.year
    t["trimestre"] = t.fecha.dt.quarter
    t["numMes"] = t.fecha.dt.month
    t["mes"] = t.numMes.map(lambda m: MESES[m - 1])
    t["anioMes"] = t.anio * 100 + t.numMes
    t["dia"] = t.fecha.dt.day
    t["semanaISO"] = t.fecha.dt.isocalendar().week.astype(int)
    t["diaSemana"] = t.fecha.dt.dayofweek + 1
    t["nombreDia"] = t.diaSemana.map(lambda d: DIAS[d - 1])
    t["esFinDeSemana"] = t.diaSemana >= 6
    t["fecha"] = t.fecha.dt.date
    dims["Tiempo"] = t[["id", "fecha", "anio", "trimestre", "numMes", "mes", "anioMes", "dia",
                        "semanaISO", "diaSemana", "nombreDia", "esFinDeSemana"]]

    # Oficina (nombre desde oficinas.csv)
    o = primero(df, "idoficina", ["idsociedad"]).rename(columns={"idoficina": "codigo", "idsociedad": "idSociedad"})
    o = o.merge(leer_nombres_oficina(), on="codigo", how="left")
    o["nombre"] = rellenar(o["nombre"])
    o["codigo"] = o["codigo"].astype(int)
    dims["Oficina"] = o[["codigo", "nombre", "idSociedad"]]

    # Ubigeo (nombres desde el geojson publico)
    u = primero(df, "ubigeo", ["cod_departamento", "cod_provincia", "cod_distrito"])
    u = u.rename(columns={"ubigeo": "codigo", "cod_departamento": "codDepartamento",
                          "cod_provincia": "codProvincia", "cod_distrito": "codDistrito"})
    u = u.merge(leer_nombres_ubigeo(), on="codigo", how="left")
    for c in ["departamento", "provincia", "distrito"]:
        u[c] = rellenar(u[c])
    dims["Ubigeo"] = u[["codigo", "codDepartamento", "codProvincia", "codDistrito", "departamento", "provincia", "distrito"]]

    # Obra: atributos de la encuesta mas reciente de cada obra
    ob = primero(df, "codigoobra", ["id_maestro_obra", "tipoejecucion_cen"],
                 ordenar_desc=["fecha_creacion_encuesta", "codencuestacensadores"])
    ob = ob.rename(columns={"codigoobra": "codigo", "id_maestro_obra": "idMaestroObra", "tipoejecucion_cen": "tipoEjecucion"})
    ob["tipoEjecucion"] = ob["tipoEjecucion"].astype("string").fillna("DESCONOCIDO")
    dims["Obra"] = ob

    te = primero(df, "id_tipo_estructura", ["tipoestructura_cen"]).rename(
        columns={"id_tipo_estructura": "codigo", "tipoestructura_cen": "nombre"})
    te["nombre"] = rellenar(te["nombre"])
    dims["TipoEstructura"] = te

    # Marca (una fila por codigotipomarcalocal)
    m = primero(df, "codigotipomarcalocal", ["destipomarca", "codigomarcalocal", "desmarca", "codlinea", "deslinea",
                                             "codsublinea", "dessublinea", "codproducto", "desproducto"])
    m = m.rename(columns={"codigotipomarcalocal": "codigo", "destipomarca": "tipoMarca", "codigomarcalocal": "codMarca",
                          "desmarca": "marca", "codlinea": "codLinea", "deslinea": "linea", "codsublinea": "codSublinea",
                          "dessublinea": "sublinea", "codproducto": "codProducto", "desproducto": "producto"})
    for c in ["tipoMarca", "marca", "linea", "sublinea", "producto"]:
        m[c] = rellenar(m[c])
    m["marcaNormalizada"] = m["marca"].str.upper()
    m["esMarcaPropia"] = m["codMarca"].isin(MARCAS_PROPIAS)
    dims["Marca"] = m[["codigo", "tipoMarca", "codMarca", "marca", "marcaNormalizada", "esMarcaPropia", "codLinea",
                       "linea", "codSublinea", "sublinea", "codProducto", "producto"]]

    um = primero(df, "codunidadmedidaisicom", ["abrevunidadmedidaisicom"]).rename(
        columns={"codunidadmedidaisicom": "codigo", "abrevunidadmedidaisicom": "abreviatura"})
    um["abreviatura"] = rellenar(um["abreviatura"])
    dims["UnidadMedida"] = um

    mo = primero(df, "codmotivoom", ["desmotivoom"]).rename(columns={"codmotivoom": "codigo", "desmotivoom": "nombre"})
    mo["nombre"] = rellenar(mo["nombre"])
    dims["Motivo"] = mo

    ej = primero(df, "codcreadorom", ["ejecutivosapvisita", "descreadorom"]).rename(
        columns={"codcreadorom": "codigo", "ejecutivosapvisita": "ejecutivoSAP", "descreadorom": "nombre"})
    ej["nombre"] = rellenar(ej["nombre"])
    dims["Ejecutivo"] = ej

    pr = pd.DataFrame({"codigo": df["codisicom_isicom_proveedor"].dropna().unique()}).sort_values("codigo")
    pr["codigo"] = pr["codigo"].astype("Int64")
    pr["nombre"] = SIN_DESC
    dims["Proveedor"] = pr.reset_index(drop=True)

    # Competencia: (0,0) ya existe como miembro -1, no se inserta de nuevo
    co = primero(df, ["comp_tipo", "comp_marca"], ["destipocompetencia_concreto", "desisicommarcacemento"])
    co = co[~((co.comp_tipo == 0) & (co.comp_marca == 0))]
    co = co.rename(columns={"comp_tipo": "codTipoCompetencia", "comp_marca": "codMarcaCemento",
                            "destipocompetencia_concreto": "tipoCompetencia", "desisicommarcacemento": "marcaCemento"})
    co["tipoCompetencia"] = rellenar(co["tipoCompetencia"])
    co["marcaCemento"] = rellenar(co["marcaCemento"])
    dims["Competencia"] = co[["codTipoCompetencia", "tipoCompetencia", "codMarcaCemento", "marcaCemento"]]
    return dims


# Llaves de negocio: columna de la dimension -> columna del origen
LLAVES = {
    "Oficina": ({"codigo": "idoficina"}, "oficinaID"),
    "Ubigeo": ({"codigo": "ubigeo"}, "ubigeoID"),
    "Obra": ({"codigo": "codigoobra"}, "obraID"),
    "TipoEstructura": ({"codigo": "id_tipo_estructura"}, "tipoEstructuraID"),
    "Marca": ({"codigo": "codigotipomarcalocal"}, "marcaID"),
    "UnidadMedida": ({"codigo": "codunidadmedidaisicom"}, "unidadMedidaID"),
    "Motivo": ({"codigo": "codmotivoom"}, "motivoID"),
    "Ejecutivo": ({"codigo": "codcreadorom"}, "ejecutivoID"),
    "Proveedor": ({"codigo": "codisicom_isicom_proveedor"}, "proveedorID"),
    "Competencia": ({"codTipoCompetencia": "comp_tipo", "codMarcaCemento": "comp_marca"}, "competenciaID"),
}


# ----------------------------------------------------------------------------- UTILIDADES DE CARGA
def _nativo(v):
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    return v


def a_filas(df):
    """DataFrame -> lista de tuplas con tipos nativos de Python y None en lugar de NaN/NA/NaT."""
    arr = df.astype(object).to_numpy()
    nulos = df.isna().to_numpy()
    return [tuple(None if n else _nativo(v) for v, n in zip(fila, mask)) for fila, mask in zip(arr, nulos)]


def insertar(cursor, tabla, df, lote=LOTE):
    cols = list(df.columns)
    sql = f"INSERT INTO {tabla} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
    filas = a_filas(df)
    for i in range(0, len(filas), lote):
        cursor.executemany(sql, filas[i:i + lote])


def cargar_dimension(cursor, tabla, df, claves):
    """Inserta la dimension y devuelve su tabla (id + llaves de negocio) para mapear la fact.
    Con cursor=None (dry-run) simula los ids."""
    if tabla == "Tiempo":
        if cursor is not None:
            insertar(cursor, tabla, df)
            cursor.commit()
        print(f"{len(df)} filas en {tabla}.")
        return df[["id"]]
    if cursor is None:
        mapa = df[claves].copy()
        mapa.insert(0, "id", range(1, len(df) + 1))
    else:
        insertar(cursor, tabla, df)
        cursor.commit()
        cursor.execute(f"SELECT id, {', '.join(claves)} FROM {tabla}")
        mapa = pd.DataFrame.from_records([tuple(r) for r in cursor.fetchall()], columns=["id"] + claves)
    print(f"{len(df)} filas en {tabla}.")
    return mapa


# ----------------------------------------------------------------------------- TABLA DE HECHOS
def construir_hechos(df, mapas):
    h = df.copy()
    for tabla, (llaves, col_id) in LLAVES.items():
        # nulos -> -1 (o 0 en competencia), para caer en el miembro DESCONOCIDO
        for _, col_origen in llaves.items():
            if col_origen not in ("ubigeo", "comp_tipo", "comp_marca"):
                h[col_origen] = h[col_origen].fillna(-1).astype("int64")
        m = mapas[tabla].rename(columns={"id": col_id})
        for col_dim, col_origen in llaves.items():
            if col_origen == "ubigeo":                 # llave de texto: mismo tipo en ambos lados
                h[col_origen] = h[col_origen].astype(object)
                m[col_dim] = m[col_dim].astype(object)
        n = len(h)
        h = h.merge(m, how="left", left_on=list(llaves.values()), right_on=list(llaves.keys()))
        if len(h) != n:
            raise ValueError(f"La dimension {tabla} tiene llaves duplicadas.")
        h = h.drop(columns=list(llaves.keys()))        # quita las llaves de la dimension para no chocar con la siguiente
        h[col_id] = h[col_id].fillna(-1).astype("int64")

    out = pd.DataFrame({
        "id": h["codencuestacensadores"].astype("int64"),
        "visitaID": h["codvisita"].fillna(0).astype("int64"),
        "tiempoID": h["iddia"].astype("int64"),
        "oficinaID": h["oficinaID"], "ubigeoID": h["ubigeoID"], "obraID": h["obraID"],
        "tipoEstructuraID": h["tipoEstructuraID"], "marcaID": h["marcaID"], "unidadMedidaID": h["unidadMedidaID"],
        "motivoID": h["motivoID"], "ejecutivoID": h["ejecutivoID"], "proveedorID": h["proveedorID"],
        "competenciaID": h["competenciaID"],
        "idSociedad": h["idsociedad"].fillna(0).astype("int64"),
        "sociedadCli6052": h["sociedad_cli_6052"], "sociedadCli6012": h["sociedad_cli_6012"],
        "tipoVisita": h["tipo_de_visita"].fillna(0).astype("int64"),
        "estado": h["estado"], "posibilidadReversion": h["posibilidadreversion_cen"],
        "flagMotivoCpsaa": h["flagmotivocpsaa"],
        "volumen": h["volumencensadoresencuesta"], "volumenRestante": h["volumenrestantecensadoresencuesta"],
        "precio": h["preciocensadoresencuesta"],
        "fechaIngreso": h["fecha_ingreso_encuesta"].dt.date,
        "fechaCreacion": h["fecha_creacion_encuesta"],
        "fechaModificacion": h["fecha_modificacion"],
        "checkin": h["checkin"], "checkout": h["checkout"],
        "checkinLatitud": h["checkin_latitud"].round(7), "checkinLongitud": h["checkin_longitud"].round(7),
        "checkoutLatitud": h["checkout_latitud"].round(7), "checkoutLongitud": h["checkout_longitud"].round(7),
        "acciones": h["desaccionesom"].str.slice(0, 500), "observacion": h["desobservacionom"].str.slice(0, 500),
    })
    # fechaCreacion es NOT NULL: si faltara, se usa el dia de la encuesta
    falta = out["fechaCreacion"].isna()
    if falta.any():
        out.loc[falta, "fechaCreacion"] = pd.to_datetime(out.loc[falta, "tiempoID"].astype(str), format="%Y%m%d")
    # los hechos no pueden apuntar a fechas fuera de Tiempo
    fuera = ~out["tiempoID"].between(FECHA_INI.year * 10000 + 101, FECHA_FIN.year * 10000 + 1231)
    if fuera.any():
        raise ValueError(f"{int(fuera.sum())} encuestas con iddia fuera del rango de Tiempo ({FECHA_INI} a {FECHA_FIN}).")
    return out


# ----------------------------------------------------------------------------- VALIDACION
def validar(cursor, hechos, dims):
    print("\n--- Validación ---")
    esperado = (len(hechos), round(float(hechos.volumen.sum()), 2),
                round(float(hechos.volumenRestante.sum()), 2), round(float(hechos.precio.sum()), 2))
    print(f"Origen  : filas={esperado[0]}, volumen={esperado[1]:,.2f}, restante={esperado[2]:,.2f}, precio={esperado[3]:,.2f}")
    if cursor is None:
        print("(dry-run: no se consulta SQL Server)")
    else:
        cursor.execute("SELECT COUNT(*), SUM(volumen), SUM(volumenRestante), SUM(precio) FROM fact_consumo")
        r = cursor.fetchone()
        real = (r[0], round(float(r[1]), 2), round(float(r[2]), 2), round(float(r[3]), 2))
        print(f"Destino : filas={real[0]}, volumen={real[1]:,.2f}, restante={real[2]:,.2f}, precio={real[3]:,.2f}")
        print("✅ Totales coinciden" if real == esperado else "❌ LOS TOTALES NO COINCIDEN, revisar")

    print("Filas en DESCONOCIDO (-1) por dimensión:")
    for col in ["oficinaID", "ubigeoID", "obraID", "tipoEstructuraID", "marcaID", "unidadMedidaID", "motivoID",
                "ejecutivoID", "proveedorID", "competenciaID"]:
        print(f"  {col:18s} {int((hechos[col] == -1).sum())}")
    print("Filas por dimensión (sin el miembro -1):", {k: len(v) for k, v in dims.items()})


# ----------------------------------------------------------------------------- PROGRAMA PRINCIPAL
def main():
    dry = "--dry-run" in sys.argv

    df = preparar_origen(leer_origen())
    print(f"{len(df)} encuestas leídas ({df.iddia.min()} a {df.iddia.max()}).")
    dims = construir_dimensiones(df)

    if dry:
        cursor = None
        conn = None
    else:
        if not crear_base_si_no_existe():
            sys.exit(1)
        conn = get_connection_destino()
        if not conn:
            sys.exit(1)
        cursor = conn.cursor()
        cursor.fast_executemany = True           # ~100 veces más rápido que insertar fila por fila
        create_datamart_schema(cursor)
        print(" Esquema completo del Data Mart creado.")

    # ----------------------------------------------------------- Cargar dimensiones
    mapas = {}
    print("Cargando Tiempo...")
    cargar_dimension(cursor, "Tiempo", dims["Tiempo"], ["id"])
    for tabla, (llaves, _) in LLAVES.items():
        print(f"Cargando {tabla}...")
        mapas[tabla] = cargar_dimension(cursor, tabla, dims[tabla], list(llaves.keys()))

    # ----------------------------------------------------------- Tabla de hechos: fact_consumo
    print("Cargando fact_consumo...")
    hechos = construir_hechos(df, mapas)
    if cursor is not None:
        insertar(cursor, "fact_consumo", hechos)
        conn.commit()
        for sentencia in INDICES:
            cursor.execute(sentencia)
        conn.commit()
    print(f"{len(hechos)} encuestas cargadas.")

    validar(cursor, hechos, dims)
    if conn:
        conn.close()
    print(" ETL completado exitosamente.")


if __name__ == "__main__":
    main()
