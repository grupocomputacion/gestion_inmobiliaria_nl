DROP TABLE IF EXISTS contratos;
DROP TABLE IF EXISTS inmuebles;
DROP TABLE IF EXISTS bloques;

CREATE TABLE bloques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL
);

CREATE TABLE inmuebles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_bloque INTEGER,
    tipo TEXT,
    precio_alquiler INTEGER,
    costo_contrato INTEGER,
    deposito_base INTEGER,
    FOREIGN KEY (id_bloque) REFERENCES bloques(id)
);

CREATE TABLE contratos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_inmueble INTEGER,
    inquilino TEXT,
    fecha_inicio DATE,
    fecha_fin DATE,
    activo INTEGER DEFAULT 1,
    monto_deuda INTEGER DEFAULT 0,
    FOREIGN KEY (id_inmueble) REFERENCES inmuebles(id)
);
