from flask import Flask, render_template_string, request, redirect, flash, send_file, session
import sqlite3
from fpdf import FPDF
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = "super_secreto_clinica_2026"

# --- CONEXIÓN A LA BASE DE DATOS EXTERNA (clinica.db) ---
def obtener_conexion():
    conexion = sqlite3.connect("clinica.db")
    conexion.row_factory = sqlite3.Row
    return conexion

# --- INICIALIZADOR Y ACTUALIZADOR AUTOMÁTICO DE LA BASE DE DATOS ---
def inicializar_bd():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        rol TEXT,
        nombres TEXT DEFAULT '',
        dni TEXT DEFAULT ''
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pacientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, dni TEXT UNIQUE, sexo TEXT DEFAULT 'No especificado',
        fecha_nacimiento TEXT, direccion TEXT, celular TEXT,
        motivo_consulta TEXT, antecedentes TEXT, diagnosticos TEXT,
        alergias TEXT, grupo_sanguineo TEXT DEFAULT 'Desconoce',
        estatura REAL DEFAULT 0, peso REAL DEFAULT 0
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS especialidades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, dni TEXT UNIQUE, cmp TEXT, especialidad_id INTEGER,
        FOREIGN KEY (especialidad_id) REFERENCES especialidades(id)
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS citas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER, medico_id INTEGER, fecha TEXT,
        estado TEXT DEFAULT 'pendiente',
        tipo_atencion TEXT DEFAULT 'Cita',
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
        FOREIGN KEY (medico_id) REFERENCES medicos(id)
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS triajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cita_id INTEGER UNIQUE,
        presion_arterial TEXT,
        temperatura REAL,
        saturacion INTEGER,
        latidos INTEGER,
        frecuencia_respiratoria INTEGER,
        peso REAL,
        talla REAL,
        imc REAL,
        FOREIGN KEY (cita_id) REFERENCES citas(id)
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS consultas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cita_id INTEGER, diagnostico TEXT, medicina TEXT,
        frecuencia TEXT, cantidad TEXT, tratamiento TEXT,
        tipo_atencion TEXT DEFAULT 'Consulta',
        FOREIGN KEY (cita_id) REFERENCES citas(id)
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, descripcion TEXT, stock INTEGER, precio REAL
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_transaccion TEXT DEFAULT 'Medicamento',
        medicamento_id INTEGER, cantidad INTEGER, total REAL,
        monto_clinica REAL DEFAULT 0, monto_medico REAL DEFAULT 0,
        medico_id INTEGER, consulta_id INTEGER,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        tipo_comprobante TEXT DEFAULT 'Ticket', documento_cliente TEXT,
        cliente_nombre TEXT
    )""")
    
    # Migraciones automáticas seguras
    try: cursor.execute("ALTER TABLE pacientes ADD COLUMN estatura REAL DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE pacientes ADD COLUMN peso REAL DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE citas ADD COLUMN tipo_atencion TEXT DEFAULT 'Cita'")
    except: pass
    try: cursor.execute("ALTER TABLE consultas ADD COLUMN tipo_atencion TEXT DEFAULT 'Consulta'")
    except: pass
    try: cursor.execute("ALTER TABLE ventas ADD COLUMN tipo_transaccion TEXT DEFAULT 'Medicamento'")
    except: pass
    try: cursor.execute("ALTER TABLE ventas ADD COLUMN monto_clinica REAL DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE ventas ADD COLUMN monto_medico REAL DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE ventas ADD COLUMN medico_id INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE ventas ADD COLUMN consulta_id INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE medicamentos ADD COLUMN descripcion TEXT")
    except: pass
    
    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO usuarios (username, password, rol, nombres, dni) VALUES ('admin', 'admin123', 'administrador', 'Administrador General', '00000000')")
        
    conexion.commit()
    conexion.close()

inicializar_bd()

def login_requerido(f):
    @wraps(f)
    def funcion_protegida(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return funcion_protegida

# --- PLANTILLA HTML: LOGIN PREMIUM ---
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Acceso Seguro - GastroClinic</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #0a0f1d;
            --card-bg: rgba(15, 23, 42, 0.85);
            --brand-primary: #0284c7;
            --brand-accent: #38bdf8;
            --text-light: #f8fafc;
        }
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: radial-gradient(circle at center, #1e293b 0%, var(--bg-deep) 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            margin: 0;
        }
        .login-card {
            background: var(--card-bg);
            backdrop-filter: blur(24px);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 24px;
            box-shadow: 0 30px 60px -15px rgba(0, 0, 0, 0.8);
            width: 420px;
            padding: 3rem 2.5rem;
            color: var(--text-light);
            animation: fadeInScale 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        @keyframes fadeInScale {
            0% { opacity: 0; transform: scale(0.95) translateY(10px); }
            100% { opacity: 1; transform: scale(1) translateY(0); }
        }
        .form-control {
            background: rgba(15, 23, 42, 0.6);
            border: 1.5px solid rgba(255, 255, 255, 0.12);
            color: #fff;
            border-radius: 12px;
            padding: 13px 18px;
            font-size: 0.95rem;
            transition: all 0.25s ease;
        }
        .form-control:focus {
            background: rgba(15, 23, 42, 0.9);
            border-color: var(--brand-accent);
            box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.2);
            color: #fff;
        }
        .btn-tech {
            background: linear-gradient(135deg, var(--brand-primary) 0%, #2563eb 100%);
            border: none;
            color: #fff;
            font-weight: 700;
            padding: 13px;
            border-radius: 12px;
            box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.5);
            transition: all 0.25s ease;
        }
        .btn-tech:hover { transform: translateY(-2px); box-shadow: 0 15px 30px -5px rgba(37, 99, 235, 0.7); color: #fff; }
    </style>
</head>
<body>
    <div class="login-card text-center">
        <div class="mb-4">
            <div class="d-inline-block p-2 rounded-4 shadow-sm bg-white mb-2">
                <img src="/logo_clinica" alt="GastroClinic" class="img-fluid rounded-3" style="max-height: 75px;">
            </div>
            <h4 class="fw-bold mt-2 mb-1 text-white tracking-tight">GastroClinic</h4>
            <p class="text-info font-monospace small" style="letter-spacing: 1px;">FANDA SYSTEM • MEDICAL SUITE</p>
        </div>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for msg in messages %}<div class="alert alert-danger py-2 border-0 rounded-3 small mb-3 shadow-sm">{{ msg }}</div>{% endfor %}
            {% endif %}
        {% endwith %}
        <form action="/login" method="POST" class="text-start">
            <div class="mb-3">
                <label class="form-label small fw-semibold text-light opacity-88">Usuario del Sistema</label>
                <input type="text" name="username" class="form-control" placeholder="Ingrese su usuario" required autofocus>
            </div>
            <div class="mb-4">
                <label class="form-label small fw-semibold text-light opacity-88">Contraseña</label>
                <input type="password" name="password" class="form-control" placeholder="••••••••" required>
            </div>
            <button type="submit" class="btn btn-tech w-100 fs-6">Acceder al Panel ➔</button>
        </form>
    </div>
</body>
</html>
"""

# --- PLANTILLA HTML: DASHBOARD PREMIUM & SISTEMA MÉDICO ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GastroClinic - Sistema Médico Profesional</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --nav-bg: #0b132b;
            --brand-primary: #0284c7;
            --brand-accent: #06b6d4;
            --brand-success: #10b981;
            --brand-danger: #f43f5e;
            --brand-warning: #f59e0b;
            --bg-body-start: #f8fafc;
            --bg-body-end: #f1f5f9;
            --card-radius: 20px;
            --transition-speed: 0.22s;
        }

        @media (prefers-reduced-motion: reduce) {
            * { animation: none !important; transition: none !important; }
        }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: linear-gradient(135deg, var(--bg-body-start) 0%, var(--bg-body-end) 100%),
                        radial-gradient(circle at 90% 10%, rgba(6, 182, 212, 0.04) 0%, transparent 40%);
            background-attachment: fixed;
            color: #334155;
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* CORRECCIÓN ABSOLUTA PARA MODALES INACCESIBLES Y BLOQUEADOS */
        .modal {
            z-index: 1055 !important;
        }
        .modal-backdrop {
            z-index: 1050 !important;
        }
        .modal-content input, 
        .modal-content select, 
        .modal-content textarea, 
        .modal-content button,
        .modal-content .form-control,
        .modal-content .form-select {
            pointer-events: auto !important;
            position: relative;
            z-index: 1060 !important;
            background-color: #ffffff !important;
            color: #1e293b !important;
            opacity: 1 !important;
        }

        .navbar-tech {
            background: linear-gradient(135deg, #0a0f1d 0%, var(--nav-bg) 100%);
            box-shadow: 0 10px 30px -5px rgba(11, 19, 43, 0.3);
            padding: 14px 28px;
            border-bottom: 2px solid rgba(56, 189, 248, 0.2);
            position: sticky;
            top: 0;
            z-index: 1030;
        }

        .ekg-container {
            width: 150px;
            height: 38px;
            display: inline-block;
            position: relative;
            overflow: hidden;
            opacity: 0.85;
        }
        .ekg-line {
            stroke: var(--brand-accent);
            stroke-width: 2.2;
            fill: none;
            stroke-dasharray: 350;
            stroke-dashoffset: 350;
            animation: ekgAnim 3s linear infinite;
        }
        @keyframes ekgAnim {
            0% { stroke-dashoffset: 350; }
            50% { stroke-dashoffset: 0; }
            100% { stroke-dashoffset: -350; }
        }

        .live-dot {
            width: 9px;
            height: 9px;
            background-color: var(--brand-success);
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 10px var(--brand-success);
            animation: pulseDot 2s infinite;
        }
        @keyframes pulseDot {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        .nav-tabs-tech {
            border: none;
            gap: 8px;
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(12px);
            padding: 10px 14px;
            border-radius: 18px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
            margin-bottom: 28px;
            border: 1px solid rgba(226, 232, 240, 0.8);
        }
        .nav-tabs-tech .nav-link {
            border: none !important;
            border-radius: 12px !important;
            color: #475569;
            font-weight: 600;
            font-size: 0.9rem;
            padding: 10px 18px;
            transition: all var(--transition-speed) ease;
        }
        .nav-tabs-tech .nav-link:hover {
            color: var(--brand-primary);
            background: rgba(2, 132, 199, 0.08);
            transform: translateY(-1.5px);
        }
        .nav-tabs-tech .nav-link.active {
            background: linear-gradient(135deg, var(--brand-primary) 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 8px 20px -4px rgba(2, 132, 199, 0.4);
            transform: translateY(-1.5px);
        }

        .card-tech {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(226, 232, 240, 0.9);
            border-radius: var(--card-radius);
            box-shadow: 0 20px 40px -10px rgba(15, 23, 42, 0.06);
            transition: all var(--transition-speed) ease;
            overflow: hidden;
        }
        .card-tech:hover {
            box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.1);
        }
        .card-header-tech {
            border-bottom: 1px solid rgba(241, 245, 249, 1);
            background: transparent;
            padding: 22px 26px;
        }

        .form-control, .form-select {
            border-radius: 12px;
            border: 1.5px solid #cbd5e1;
            background: rgba(255, 255, 255, 0.95);
            padding: 12px 16px;
            font-size: 0.93rem;
            color: #1e293b;
            transition: all var(--transition-speed) ease;
        }
        .form-control:focus, .form-select:focus {
            border-color: var(--brand-primary);
            background: #ffffff;
            box-shadow: 0 0 0 4px rgba(2, 132, 199, 0.12);
        }
        .form-label {
            font-weight: 600;
            color: #334155;
            font-size: 0.88rem;
            margin-bottom: 6px;
        }

        .btn-action-primary {
            background: linear-gradient(135deg, var(--brand-primary) 0%, #2563eb 100%);
            border: none;
            color: #fff;
            font-weight: 700;
            border-radius: 12px;
            padding: 12px 22px;
            box-shadow: 0 8px 20px -4px rgba(2, 132, 199, 0.35);
            transition: all var(--transition-speed) ease;
        }
        .btn-action-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 25px -4px rgba(2, 132, 199, 0.5);
            color: #fff;
        }

        .table-tech th {
            background: rgba(241, 245, 249, 0.9);
            color: #475569;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            padding: 14px 18px;
            border-bottom: 2px solid #e2e8f0;
        }
        .table-tech td {
            padding: 15px 18px;
            vertical-align: middle;
            color: #334155;
            border-color: #f1f5f9;
            font-size: 0.92rem;
        }
        .table-tech tbody tr {
            transition: background-color 0.15s ease;
        }
        .table-tech tbody tr:hover {
            background-color: rgba(2, 132, 199, 0.03);
        }

        .badge-soft-primary { background: #e0f2fe; color: #0369a1; font-weight: 700; border-radius: 8px; padding: 6px 12px; font-size: 0.78rem; }
        .badge-soft-danger { background: #ffe4e6; color: #9f1239; font-weight: 700; border-radius: 8px; padding: 6px 12px; font-size: 0.78rem; }
        .badge-soft-success { background: #dcfce7; color: #166534; font-weight: 700; border-radius: 8px; padding: 6px 12px; font-size: 0.78rem; }
        .badge-soft-info { background: #cffafe; color: #0e7490; font-weight: 700; border-radius: 8px; padding: 6px 12px; font-size: 0.78rem; }
        
        .tab-pane {
            animation: fadeInTab 0.3s ease-out forwards;
        }
        @keyframes fadeInTab {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>

    <nav class="navbar navbar-dark navbar-tech mb-4">
        <div class="container-fluid px-4 d-flex justify-content-between align-items-center">
            <div class="d-flex align-items-center gap-3">
                <div class="bg-white p-1 rounded-3 shadow-sm">
                    <img src="/logo_clinica" alt="Logo" height="38" class="rounded-2">
                </div>
                <div>
                    <span class="fw-bold text-white fs-5 tracking-tight">GastroClinic</span>
                    <div class="d-flex align-items-center gap-2">
                        <span class="live-dot"></span>
                        <small class="text-info font-monospace" style="font-size: 0.7rem; letter-spacing: 0.5px;">SISTEMA CLÍNICO ACTIVO</small>
                    </div>
                </div>
                <div class="ekg-container d-none d-md-block ms-3">
                    <svg viewBox="0 0 150 40" width="150" height="38">
                        <path class="ekg-line" d="M0,20 L30,20 L38,6 L45,34 L54,12 L62,26 L70,20 L150,20" />
                    </svg>
                </div>
            </div>
            
            <div class="d-flex align-items-center gap-3">
                <div class="text-light small bg-slate-800 px-3 py-2 rounded-3 border border-secondary border-opacity-25 shadow-sm">
                    👤 <strong class="text-info">{{ session['username']|capitalize }}</strong> 
                    <span class="badge bg-secondary ms-1 opacity-88">{{ session['rol']|capitalize }}</span>
                </div>
                <a href="/logout" class="btn btn-outline-light btn-sm fw-bold rounded-3 px-3 shadow-sm transition-all hover-scale">Salir 🚪</a>
            </div>
        </div>
    </nav>

    <div class="container-fluid px-4">
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="alert alert-success border-0 shadow-sm rounded-4 mb-4 alert-dismissible fade show" role="alert">
                {{ message|safe }}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <!-- PESTAÑAS DE NAVEGACIÓN -->
        <ul class="nav nav-tabs-tech" id="clinicaTabs" role="tablist">
            <li class="nav-item"><button class="nav-link active" id="pacientes-tab" data-bs-toggle="tab" data-bs-target="#pacientes" type="button">👤 Pacientes & Fichas</button></li>
            <li class="nav-item"><button class="nav-link" id="citas-tab" data-bs-toggle="tab" data-bs-target="#citas" type="button">📅 Agenda Citas & Controles</button></li>
            
            {% if session['rol'] in ['administrador', 'medico', 'secretaria'] %}
            <li class="nav-item"><button class="nav-link text-warning fw-bold" id="triaje-tab" data-bs-toggle="tab" data-bs-target="#triaje" type="button">🩺 Módulo de Triaje</button></li>
            {% endif %}

            {% if session['rol'] in ['administrador', 'medico'] %}
            <li class="nav-item"><button class="nav-link" id="consultas-tab" data-bs-toggle="tab" data-bs-target="#consultas" type="button">🩺 Consultas Médicas</button></li>
            {% endif %}
            
            {% if session['rol'] in ['administrador', 'secretaria', 'cajero'] %}
            <li class="nav-item"><button class="nav-link" id="farmacia-tab" data-bs-toggle="tab" data-bs-target="#farmacia" type="button">💊 Farmacia & Caja</button></li>
            {% endif %}
            
            {% if session['rol'] in ['administrador', 'secretaria', 'cajero'] %}
            <li class="nav-item"><button class="nav-link text-success fw-bold" id="reportes-tab" data-bs-toggle="tab" data-bs-target="#reportes" type="button">📊 Reportes & Finanzas</button></li>
            {% endif %}
            
            {% if session['rol'] == 'administrador' %}
            <li class="nav-item"><button class="nav-link text-primary" id="medicos-tab" data-bs-toggle="tab" data-bs-target="#medicos" type="button">👨‍⚕️ Staff Médicos</button></li>
            <li class="nav-item"><button class="nav-link text-warning" id="usuarios-tab" data-bs-toggle="tab" data-bs-target="#usuarios" type="button">⚙️ Config. Usuarios</button></li>
            {% endif %}
        </ul>

        <div class="tab-content mb-5">
            
            <!-- PESTAÑA: PACIENTES -->
            <div class="tab-pane fade show active" id="pacientes">
                <div class="card-tech mb-4">
                    <div class="card-header-tech d-flex justify-content-between align-items-center">
                        <h5 class="fw-bold m-0 text-primary">📝 Apertura de Nueva Ficha Médica</h5>
                        <span class="badge badge-soft-primary">Historia Clínica Digital</span>
                    </div>
                    <div class="card-body p-4">
                        <form action="/agregar_paciente" method="POST">
                            <h6 class="fw-bold text-secondary mb-3 pb-2 border-bottom">1. Datos Personales</h6>
                            <div class="row g-3 mb-4">
                                <div class="col-md-3"><label class="form-label">Nombre Completo</label><input type="text" name="nombre" class="form-control" required placeholder="Ej. Ana Torres"></div>
                                <div class="col-md-2"><label class="form-label">DNI</label><input type="text" name="dni" class="form-control" required placeholder="8 dígitos"></div>
                                <div class="col-md-2"><label class="form-label">F. Nacimiento</label><input type="date" name="fecha_nacimiento" class="form-control" required></div>
                                <div class="col-md-2"><label class="form-label">Sexo</label><select name="sexo" class="form-select" required><option value="Masculino">Masculino</option><option value="Femenino">Femenino</option><option value="Otro">Otro</option></select></div>
                                <div class="col-md-3"><label class="form-label">Celular</label><input type="text" name="celular" class="form-control" placeholder="987654321"></div>
                                <div class="col-md-12"><label class="form-label">Dirección</label><input type="text" name="direccion" class="form-control" placeholder="Jr. Los Pinos #456"></div>
                            </div>

                            <h6 class="fw-bold text-secondary mb-3 pb-2 border-bottom">2. Perfil Clínico & Antropometría Base</h6>
                            <div class="row g-3 mb-4">
                                <div class="col-md-3">
                                    <label class="form-label text-danger">Grupo Sanguíneo</label>
                                    <select name="grupo_sanguineo" class="form-select border-danger">
                                        <option value="Desconoce">Desconoce</option>
                                        <option value="O+">O+</option><option value="O-">O-</option>
                                        <option value="A+">A+</option><option value="A-">A-</option>
                                        <option value="B+">B+</option><option value="B-">B-</option>
                                        <option value="AB+">AB+</option><option value="AB-">AB-</option>
                                    </select>
                                </div>
                                <div class="col-md-2"><label class="form-label text-primary">Estatura (m)</label><input type="number" step="0.01" name="estatura" class="form-control border-primary" placeholder="Ej. 1.72" min="0" max="3"></div>
                                <div class="col-md-2"><label class="form-label text-primary">Peso (kg)</label><input type="number" step="0.1" name="peso" class="form-control border-primary" placeholder="Ej. 70.5" min="0" max="500"></div>
                                <div class="col-md-5"><label class="form-label text-danger">Alergias</label><textarea name="alergias" class="form-control border-danger" rows="1" placeholder="Ej. Ninguna"></textarea></div>
                                
                                <div class="col-md-12"><label class="form-label">Motivo de Consulta</label><textarea name="motivo_consulta" class="form-control" rows="1" placeholder="Síntomas..."></textarea></div>
                                <div class="col-md-6"><label class="form-label">Antecedentes</label><textarea name="antecedentes" class="form-control" rows="2" placeholder="Enfermedades pasadas..."></textarea></div>
                                <div class="col-md-6"><label class="form-label">Diagnósticos Previos</label><textarea name="diagnosticos" class="form-control" rows="2" placeholder="Historial clínico..."></textarea></div>
                            </div>
                            <button type="submit" class="btn btn-action-primary w-100 fs-6">💾 Guardar Ficha Médica</button>
                        </form>
                    </div>
                </div>

                <div class="card-tech">
                    <div class="card-header-tech"><h5 class="fw-bold m-0 text-dark">📋 Directorio de Pacientes</h5></div>
                    <div class="table-responsive">
                        <table class="table table-tech align-middle mb-0">
                            <thead><tr><th>ID</th><th>Paciente</th><th>DNI</th><th>Medidas (Alt/Peso)</th><th>Sangre</th><th>Alergias</th><th>Acciones</th></tr></thead>
                            <tbody>
                                {% for p in pacientes %}
                                <tr>
                                    <td class="fw-bold text-muted">#{{ p.id }}</td>
                                    <td><div class="fw-bold text-dark">{{ p.nombre }}</div><small class="text-muted">{{ p.sexo }} • {{ p.celular or 'Sin Celular' }}</small></td>
                                    <td><span class="badge bg-light text-dark border">{{ p.dni }}</span></td>
                                    <td><span class="text-primary fw-semibold">{{ p.estatura }} m</span> / <span class="text-success fw-semibold">{{ p.peso }} kg</span></td>
                                    <td><span class="badge badge-soft-danger">{{ p.grupo_sanguineo }}</span></td>
                                    <td><small class="text-danger fw-semibold">{{ p.alergias or 'Ninguna' }}</small></td>
                                    <td>
                                        <div class="d-flex gap-1">
                                            <a href="/descargar_historia_paciente/{{ p.id }}" target="_blank" class="btn btn-outline-primary btn-sm fw-bold rounded-3" title="Ver Historia">📄</a>
                                            <button class="btn btn-outline-warning btn-sm fw-bold rounded-3" data-bs-toggle="modal" data-bs-target="#modalEditarPaciente{{ p.id }}" title="Editar Paciente">✏️</button>
                                        </div>
                                    </td>
                                </tr>

                                <!-- MODAL EDITAR PACIENTE -->
                                <div class="modal fade" id="modalEditarPaciente{{ p.id }}" tabindex="-1">
                                    <div class="modal-dialog modal-lg">
                                        <div class="modal-content card-tech p-3">
                                            <div class="modal-header border-0"><h5 class="fw-bold text-primary">✏️ Editar Ficha de Paciente: {{ p.nombre }}</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
                                            <div class="modal-body">
                                                <form action="/editar_paciente/{{ p.id }}" method="POST">
                                                    <div class="row g-3 mb-3">
                                                        <div class="col-md-6"><label class="form-label">Nombre Completo</label><input type="text" name="nombre" class="form-control" value="{{ p.nombre }}" required></div>
                                                        <div class="col-md-6"><label class="form-label">DNI</label><input type="text" name="dni" class="form-control" value="{{ p.dni }}" required></div>
                                                        <div class="col-md-4"><label class="form-label">F. Nacimiento</label><input type="date" name="fecha_nacimiento" class="form-control" value="{{ p.fecha_nacimiento }}" required></div>
                                                        <div class="col-md-4"><label class="form-label">Sexo</label><select name="sexo" class="form-select" required><option value="Masculino" {% if p.sexo=='Masculino' %}selected{% endif %}>Masculino</option><option value="Femenino" {% if p.sexo=='Femenino' %}selected{% endif %}>Femenino</option><option value="Otro" {% if p.sexo=='Otro' %}selected{% endif %}>Otro</option></select></div>
                                                        <div class="col-md-4"><label class="form-label">Celular</label><input type="text" name="celular" class="form-control" value="{{ p.celular }}"></div>
                                                        <div class="col-md-12"><label class="form-label">Dirección</label><input type="text" name="direccion" class="form-control" value="{{ p.direccion }}"></div>
                                                        <div class="col-md-3">
                                                            <label class="form-label text-danger">Grupo Sanguíneo</label>
                                                            <select name="grupo_sanguineo" class="form-select border-danger">
                                                                <option value="Desconoce" {% if p.grupo_sanguineo=='Desconoce' %}selected{% endif %}>Desconoce</option>
                                                                <option value="O+" {% if p.grupo_sanguineo=='O+' %}selected{% endif %}>O+</option><option value="O-" {% if p.grupo_sanguineo=='O-' %}selected{% endif %}>O-</option>
                                                                <option value="A+" {% if p.grupo_sanguineo=='A+' %}selected{% endif %}>A+</option><option value="A-" {% if p.grupo_sanguineo=='A-' %}selected{% endif %}>A-</option>
                                                                <option value="B+" {% if p.grupo_sanguineo=='B+' %}selected{% endif %}>B+</option><option value="B-" {% if p.grupo_sanguineo=='B-' %}selected{% endif %}>B-</option>
                                                                <option value="AB+" {% if p.grupo_sanguineo=='AB+' %}selected{% endif %}>AB+</option><option value="AB-" {% if p.grupo_sanguineo=='AB-' %}selected{% endif %}>AB-</option>
                                                            </select>
                                                        </div>
                                                        <div class="col-md-2"><label class="form-label text-primary">Estatura (m)</label><input type="number" step="0.01" name="estatura" class="form-control border-primary" value="{{ p.estatura }}"></div>
                                                        <div class="col-md-2"><label class="form-label text-primary">Peso (kg)</label><input type="number" step="0.1" name="peso" class="form-control border-primary" value="{{ p.peso }}"></div>
                                                        <div class="col-md-5"><label class="form-label text-danger">Alergias</label><textarea name="alergias" class="form-control border-danger" rows="1">{{ p.alergias }}</textarea></div>
                                                        <div class="col-md-12"><label class="form-label">Motivo de Consulta</label><textarea name="motivo_consulta" class="form-control" rows="1">{{ p.motivo_consulta }}</textarea></div>
                                                        <div class="col-md-6"><label class="form-label">Antecedentes</label><textarea name="antecedentes" class="form-control" rows="2">{{ p.antecedentes }}</textarea></div>
                                                        <div class="col-md-6"><label class="form-label">Diagnósticos Previos</label><textarea name="diagnosticos" class="form-control" rows="2">{{ p.diagnosticos }}</textarea></div>
                                                    </div>
                                                    <button type="submit" class="btn btn-warning w-100 fw-bold text-dark">💾 Guardar Cambios</button>
                                                </form>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- PESTAÑA: CITAS Y CONTROLES -->
            <div class="tab-pane fade" id="citas">
                <div class="row g-4">
                    <div class="col-md-4">
                        <div class="card-tech p-4">
                            <h5 class="fw-bold text-success mb-3">📅 Agendar Cita o Control</h5>
                            <form action="/agendar_cita" method="POST">
                                <div class="mb-3">
                                    <label class="form-label fw-semibold text-primary">📌 Tipo de Atención</label>
                                    <select name="tipo_atencion" class="form-select border-primary fw-bold" required>
                                        <option value="Cita">Cita (Genera Cobro / Caja)</option>
                                        <option value="Control">Control (Gratuito / Seguimiento Clínico)</option>
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">🔍 Buscar Paciente (Nombre o DNI)</label>
                                    <input type="text" id="buscadorPacienteCita" class="form-control mb-2" placeholder="Escriba para filtrar..." onkeyup="filtrarSelectPacientes()">
                                    <label class="form-label">Seleccionar Paciente Filtrado</label>
                                    <select name="paciente_id" id="selectPacienteCita" class="form-select" required size="4" style="height: 120px;">
                                        {% for p in pacientes %}<option value="{{ p.id }}">{{ p.nombre }} - DNI: {{ p.dni }}</option>{% endfor %}
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Médico</label>
                                    <select name="medico_id" class="form-select" required>
                                        <option value="">-- Seleccionar Médico --</option>
                                        {% for m in medicos %}<option value="{{ m.id }}">Dr/a. {{ m.nombre }} ({{ m.especialidad }})</option>{% endfor %}
                                    </select>
                                </div>
                                <div class="row g-2 mb-4">
                                    <div class="col-md-6">
                                        <label class="form-label">Fecha</label>
                                        <input type="date" name="fecha_cita" class="form-control" required>
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">Hora</label>
                                        <select name="hora_cita" class="form-select fw-bold" required>
                                            <option value="08">08</option><option value="09">09</option><option value="10">10</option>
                                            <option value="11">11</option><option value="12">12</option><option value="13">13</option>
                                            <option value="14">14</option><option value="15">15</option><option value="16">16</option>
                                            <option value="17">17</option><option value="18">18</option><option value="19">19</option>
                                        </select>
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">Minutos</label>
                                        <select name="minuto_cita" class="form-select fw-bold text-primary" required>
                                            <option value="00">00</option>
                                            <option value="15">15</option>
                                            <option value="30">30</option>
                                            <option value="45">45</option>
                                        </select>
                                    </div>
                                </div>
                                <button type="submit" class="btn btn-success w-100 fw-bold rounded-3 py-2">✅ Confirmar Registro</button>
                            </form>
                        </div>
                    </div>
                    <div class="col-md-8">
                        <div class="card-tech">
                            <div class="card-header-tech"><h5 class="fw-bold m-0">🗓️ Agenda de Citas y Controles Pendientes</h5></div>
                            <div class="table-responsive">
                                <table class="table table-tech align-middle mb-0">
                                    <thead><tr><th>Tipo</th><th>Fecha / Hora</th><th>Médico</th><th>Paciente</th><th>Acciones</th></tr></thead>
                                    <tbody>
                                        {% for c in citas %}
                                        <tr>
                                            <td>
                                                {% if c.tipo_atencion == 'Control' %}
                                                    <span class="badge badge-soft-info">CONTROL</span>
                                                {% else %}
                                                    <span class="badge badge-soft-success">CITA</span>
                                                {% endif %}
                                            </td>
                                            <td class="fw-bold text-primary">{{ c.fecha }}</td>
                                            <td><div class="fw-semibold">Dr/a. {{ c.medico_nombre or 'General' }}</div><small class="text-muted">{{ c.especialidad or 'General' }}</small></td>
                                            <td class="fw-bold">{{ c.paciente_nombre }}</td>
                                            <td>
                                                <div class="d-flex gap-1">
                                                    <button type="button" class="btn btn-outline-warning btn-sm fw-bold rounded-3 btn-editar-cita" 
                                                            data-id="{{ c.id }}" 
                                                            data-tipo="{{ c.tipo_atencion }}" 
                                                            data-medico="{{ c.medico_id }}" 
                                                            data-fecha="{{ c.fecha }}" 
                                                            title="Editar Cita">✏️</button>
                                                    <a href="/eliminar_cita/{{ c.id }}" class="btn btn-outline-danger btn-sm fw-bold rounded-3" onclick="return confirm('¿Eliminar esta cita?');" title="Eliminar Cita">🗑️</a>
                                                </div>
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- MODAL ÚNICO GLOBAL PARA EDITAR CITAS -->
                        <div class="modal fade" id="modalEditarCitaUnico" tabindex="-1" aria-hidden="true">
                            <div class="modal-dialog">
                                <div class="modal-content card-tech p-3 shadow-lg border-success">
                                    <div class="modal-header border-0">
                                        <h5 class="fw-bold text-success">✏️ Editar Cita / Control</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                    </div>
                                    <div class="modal-body">
                                        <form id="formEditarCita" method="POST">
                                            <div class="mb-3">
                                                <label class="form-label">Tipo de Atención</label>
                                                <select name="tipo_atencion" id="editTipoAtencion" class="form-select fw-bold" required>
                                                    <option value="Cita">Cita</option>
                                                    <option value="Control">Control</option>
                                                </select>
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label">Médico Asignado</label>
                                                <select name="medico_id" id="editMedicoId" class="form-select fw-bold text-primary" required>
                                                    {% for med in medicos %}
                                                    <option value="{{ med.id }}">Dr/a. {{ med.nombre }} ({{ med.especialidad }})</option>
                                                    {% endfor %}
                                                </select>
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label">Fecha y Hora (AAAA-MM-DD HH:MM:SS)</label>
                                                <input type="text" name="fecha" id="editFechaCita" class="form-control fw-bold text-dark" required>
                                            </div>
                                            <button type="submit" class="btn btn-success w-100 fw-bold rounded-3 py-2 shadow-sm">💾 Actualizar Cita</button>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <script>
                            document.addEventListener("DOMContentLoaded", function() {
                                document.querySelectorAll('.btn-editar-cita').forEach(button => {
                                    button.addEventListener('click', function() {
                                        let id = this.getAttribute('data-id');
                                        let tipo = this.getAttribute('data-tipo');
                                        let medico = this.getAttribute('data-medico');
                                        let fecha = this.getAttribute('data-fecha');

                                        document.getElementById('formEditarCita').action = '/editar_cita/' + id;
                                        document.getElementById('editTipoAtencion').value = tipo;
                                        document.getElementById('editMedicoId').value = medico;
                                        document.getElementById('editFechaCita').value = fecha;

                                        let myModal = new bootstrap.Modal(document.getElementById('modalEditarCitaUnico'));
                                        myModal.show();
                                    });
                                });
                            });
                        </script>

                    </div>
                </div>
            </div>
            <script>
                function filtrarSelectPacientes() {
                    let filtro = document.getElementById("buscadorPacienteCita").value.toLowerCase();
                    let select = document.getElementById("selectPacienteCita");
                    let opciones = select.options;
                    for (let i = 0; i < opciones.length; i++) {
                        let texto = opciones[i].text.toLowerCase();
                        opciones[i].style.display = texto.includes(filtro) ? "" : "none";
                    }
                }
            </script>

            {% if session['rol'] in ['administrador', 'medico', 'secretaria'] %}
            <!-- PESTAÑA: TRIAJE -->
            <div class="tab-pane fade" id="triaje">
                <div class="row g-4">
                    <div class="col-md-5">
                        <div class="card-tech p-4 border-warning">
                            <h5 class="fw-bold text-warning mb-3">🩺 Registrar Signos Vitales (Triaje)</h5>
                            <form action="/registrar_triaje" method="POST">
                                <div class="mb-3">
                                    <label class="form-label">Seleccionar Cita / Paciente Pendiente</label>
                                    <select name="cita_id" id="selectCitaTriaje" class="form-select border-warning fw-bold" required>
                                        <option value="">-- Seleccionar Cita --</option>
                                        {% for c in citas %}
                                        <option value="{{ c.id }}" data-peso="{{ c.peso }}" data-talla="{{ c.estatura }}">[{{ c.tipo_atencion|upper }}] {{ c.paciente_nombre }} - Dr/a. {{ c.medico_nombre }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                                <div class="row g-2 mb-2">
                                    <div class="col-md-6"><label class="form-label small">Presión Arterial (mmHg)</label><input type="text" name="presion_arterial" class="form-control" placeholder="Ej. 120/80" required></div>
                                    <div class="col-md-6"><label class="form-label small">Temperatura (°C)</label><input type="number" step="0.1" name="temperatura" class="form-control" placeholder="Ej. 36.5" required></div>
                                </div>
                                <div class="row g-2 mb-2">
                                    <div class="col-md-6"><label class="form-label small">Saturación O2 (%)</label><input type="number" name="saturacion" class="form-control" placeholder="Ej. 98" min="50" max="100" required></div>
                                    <div class="col-md-6"><label class="form-label small">Latidos / min (lpm)</label><input type="number" name="latidos" class="form-control" placeholder="Ej. 75" min="30" max="250" required></div>
                                </div>
                                <div class="row g-2 mb-3">
                                    <div class="col-md-12"><label class="form-label small">Frecuencia Respiratoria (rpm)</label><input type="number" name="frecuencia_respiratoria" class="form-control" placeholder="Ej. 18" min="5" max="80" required></div>
                                </div>
                                
                                <h6 class="fw-bold text-primary mb-2 border-top pt-2">Antropometría & IMC</h6>
                                <div class="row g-2 mb-3">
                                    <div class="col-md-4"><label class="form-label small">Peso (kg)</label><input type="number" step="0.1" name="peso" id="pesoTriaje" class="form-control" placeholder="70.5" oninput="calcularIMC()" required></div>
                                    <div class="col-md-4"><label class="form-label small">Talla (m)</label><input type="number" step="0.01" name="talla" id="tallaTriaje" class="form-control" placeholder="1.72" oninput="calcularIMC()" required></div>
                                    <div class="col-md-4"><label class="form-label small fw-bold text-success">IMC Automático</label><input type="text" id="imcTriajeDisplay" class="form-control bg-light fw-bold text-success" readonly placeholder="0.0"></div>
                                    <input type="hidden" name="imc" id="imcTriajeInput">
                                </div>
                                
                                <button type="submit" class="btn btn-warning w-100 fw-bold rounded-3 py-2 text-dark">💾 Guardar Triaje</button>
                            </form>
                        </div>
                    </div>
                    <script>
                        document.getElementById("selectCitaTriaje").addEventListener("change", function() {
                            let option = this.options[this.selectedIndex];
                            let peso = option.getAttribute("data-peso") || "";
                            let talla = option.getAttribute("data-talla") || "";
                            document.getElementById("pesoTriaje").value = peso;
                            document.getElementById("tallaTriaje").value = talla;
                            calcularIMC();
                        });
                        function calcularIMC() {
                            let peso = parseFloat(document.getElementById("pesoTriaje").value) || 0;
                            let talla = parseFloat(document.getElementById("tallaTriaje").value) || 0;
                            if(peso > 0 && talla > 0) {
                                let imc = peso / (talla * talla);
                                document.getElementById("imcTriajeDisplay").value = imc.toFixed(2);
                                document.getElementById("imcTriajeInput").value = imc.toFixed(2);
                            } else {
                                document.getElementById("imcTriajeDisplay").value = "0.0";
                                document.getElementById("imcTriajeInput").value = "0.0";
                            }
                        }
                    </script>
                    <div class="col-md-7">
                        <div class="card-tech">
                            <div class="card-header-tech"><h5 class="fw-bold m-0">📋 Registros de Triaje Realizados</h5></div>
                            <div class="table-responsive" style="max-height: 500px; overflow-y: auto;">
                                <table class="table table-tech align-middle mb-0">
                                    <thead><tr><th>Paciente / Fecha</th><th>Signos Vitales</th><th>Antropometría & IMC</th><th>Acciones</th></tr></thead>
                                    <tbody>
                                        {% for t in triajes %}
                                        <tr>
                                            <td><div class="fw-bold text-primary">{{ t.paciente_nombre }}</div><small class="text-muted">{{ t.fecha }}</small></td>
                                            <td>
                                                <small>
                                                    ❤️ P.A: <strong>{{ t.presion_arterial }}</strong> | 
                                                    🌡️ Temp: <strong>{{ t.temperatura }}°C</strong><br>
                                                    💨 Sat O2: <strong>{{ t.saturacion }}%</strong> | 
                                                    💓 Pulso: <strong>{{ t.latidos }} lpm</strong> | 
                                                    🫁 Resp: <strong>{{ t.frecuencia_respiratoria }} rpm</strong>
                                                </small>
                                            </td>
                                            <td>
                                                <span class="badge badge-soft-success">Peso: {{ t.peso }} kg</span>
                                                <span class="badge badge-soft-primary">Talla: {{ t.talla }} m</span>
                                                <div class="small fw-bold text-dark mt-1">IMC: {{ t.imc }}</div>
                                            </td>
                                            <td>
                                                <button class="btn btn-outline-warning btn-sm fw-bold rounded-3" data-bs-toggle="modal" data-bs-target="#modalEditarTriaje{{ t.id }}" title="Editar Triaje">✏️</button>
                                            </td>
                                        </tr>

                                        <!-- MODAL EDITAR TRIAJE -->
                                        <div class="modal fade" id="modalEditarTriaje{{ t.id }}" tabindex="-1">
                                            <div class="modal-dialog">
                                                <div class="modal-content card-tech p-3">
                                                    <div class="modal-header border-0"><h5 class="fw-bold text-warning text-dark">✏️ Editar Triaje: {{ t.paciente_nombre }}</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
                                                    <div class="modal-body">
                                                        <form action="/editar_triaje/{{ t.id }}" method="POST">
                                                            <div class="mb-2"><label class="form-label">Presión Arterial (mmHg)</label><input type="text" name="presion_arterial" class="form-control" value="{{ t.presion_arterial }}" required></div>
                                                            <div class="mb-2"><label class="form-label">Temperatura (°C)</label><input type="number" step="0.1" name="temperatura" class="form-control" value="{{ t.temperatura }}" required></div>
                                                            <div class="mb-2"><label class="form-label">Saturación O2 (%)</label><input type="number" name="saturacion" class="form-control" value="{{ t.saturacion }}" required></div>
                                                            <div class="mb-2"><label class="form-label">Latidos / min (lpm)</label><input type="number" name="latidos" class="form-control" value="{{ t.latidos }}" required></div>
                                                            <div class="mb-2"><label class="form-label">Frecuencia Respiratoria (rpm)</label><input type="number" name="frecuencia_respiratoria" class="form-control" value="{{ t.frecuencia_respiratoria }}" required></div>
                                                            <div class="row g-2 mb-3">
                                                                <div class="col-md-6"><label class="form-label">Peso (kg)</label><input type="number" step="0.1" name="peso" class="form-control" value="{{ t.peso }}" required></div>
                                                                <div class="col-md-6"><label class="form-label">Talla (m)</label><input type="number" step="0.01" name="talla" class="form-control" value="{{ t.talla }}" required></div>
                                                            </div>
                                                            <button type="submit" class="btn btn-warning w-100 fw-bold text-dark">💾 Actualizar Triaje</button>
                                                        </form>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {% endif %}

            {% if session['rol'] in ['administrador', 'medico'] %}
            <!-- PESTAÑA: CONSULTAS -->
            <div class="tab-pane fade" id="consultas">
                <div class="row g-4">
                    <div class="col-md-4">
                        <div class="card-tech p-4 border-danger">
                            <h5 class="fw-bold text-danger mb-3">🩺 Registrar Atención / Control</h5>
                            <form action="/registrar_consulta" method="POST">
                                <div class="mb-3">
                                    <label class="form-label">Paciente en Espera / Cita</label>
                                    <select name="cita_id" class="form-select border-danger" required>
                                        <option value="">-- Seleccionar Cita o Control --</option>
                                        {% for c in citas %}
                                        <option value="{{ c.id }}">[{{ c.tipo_atencion|upper }}] {{ c.paciente_nombre }} - DNI: {{ c.paciente_dni }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Diagnóstico / Evolución del Control</label>
                                    <textarea name="diagnostico" class="form-control" rows="3" required placeholder="Escriba el diagnóstico o notas de control..."></textarea>
                                </div>
                                <hr class="my-3">
                                <h6 class="fw-bold text-primary mb-2">Prescripción (Opcional)</h6>
                                <div class="mb-2"><input type="text" name="medicina" class="form-control" placeholder="Medicina (ej. Amoxicilina)"></div>
                                <div class="mb-2"><input type="text" name="frecuencia" class="form-control" placeholder="Indicaciones (ej. Cada 8h)"></div>
                                <div class="mb-4"><input type="text" name="cantidad" class="form-control" placeholder="Cantidad (ej. 15 tabletas)"></div>
                                <button type="submit" class="btn btn-danger w-100 fw-bold rounded-3 py-2">💾 Guardar & Receta PDF</button>
                            </form>
                        </div>
                    </div>
                    <div class="col-md-8">
                        <div class="card-tech">
                            <div class="card-header-tech d-flex justify-content-between align-items-center">
                                <h5 class="fw-bold m-0">📚 Historial de Consultas y Controles</h5>
                                <input type="text" id="buscadorHistorial" class="form-control form-control-sm w-50" placeholder="🔍 Buscar..." onkeyup="filtrarHistorial()">
                            </div>
                            <div class="table-responsive" style="max-height: 500px; overflow-y: auto;">
                                <table class="table table-tech align-middle mb-0" id="tablaHistorial">
                                    <thead><tr><th>Fecha / Tipo</th><th>Paciente</th><th>Diagnóstico</th><th>Médico</th><th>Acciones</th></tr></thead>
                                    <tbody>
                                        {% for cons in consultas %}
                                        <tr class="fila-historial">
                                            <td>
                                                <small class="fw-bold text-primary">{{ cons.fecha }}</small><br>
                                                {% if cons.tipo_atencion == 'Control' %}
                                                    <span class="badge badge-soft-info" style="font-size: 0.68rem;">CONTROL</span>
                                                {% else %}
                                                    <span class="badge badge-soft-success" style="font-size: 0.68rem;">CONSULTA</span>
                                                {% endif %}
                                            </td>
                                            <td class="nombre-dni"><div class="fw-bold">{{ cons.paciente_nombre }}</div><small class="text-muted">DNI: {{ cons.paciente_dni }}</small></td>
                                            <td><div style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ cons.diagnostico }}</div></td>
                                            <td>Dr/a. {{ cons.medico_nombre }}</td>
                                            <td>
                                                <div class="d-flex gap-1">
                                                    <a href="/descargar_receta/{{ cons.id }}" target="_blank" class="btn btn-outline-danger btn-sm fw-bold rounded-3" title="Descargar PDF">📄</a>
                                                    <button class="btn btn-outline-warning btn-sm fw-bold rounded-3" data-bs-toggle="modal" data-bs-target="#modalEditarConsulta{{ cons.id }}" title="Editar Receta">✏️</button>
                                                </div>
                                            </td>
                                        </tr>

                                        <!-- MODAL EDITAR CONSULTA / RECETA -->
                                        <div class="modal fade" id="modalEditarConsulta{{ cons.id }}" tabindex="-1">
                                            <div class="modal-dialog">
                                                <div class="modal-content card-tech p-3">
                                                    <div class="modal-header border-0"><h5 class="fw-bold text-danger">✏️ Editar Consulta / Receta</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
                                                    <div class="modal-body">
                                                        <form action="/editar_consulta/{{ cons.id }}" method="POST">
                                                            <div class="mb-3">
                                                                <label class="form-label">Diagnóstico / Notas</label>
                                                                <textarea name="diagnostico" class="form-control" rows="3" required>{{ cons.diagnostico }}</textarea>
                                                            </div>
                                                            <div class="mb-2"><label class="form-label">Medicamento</label><input type="text" name="medicina" class="form-control" value="{{ cons.medicina }}"></div>
                                                            <div class="mb-2"><label class="form-label">Indicaciones / Frecuencia</label><input type="text" name="frecuencia" class="form-control" value="{{ cons.frecuencia }}"></div>
                                                            <div class="mb-3"><label class="form-label">Cantidad</label><input type="text" name="cantidad" class="form-control" value="{{ cons.cantidad }}"></div>
                                                            <button type="submit" class="btn btn-danger w-100 fw-bold">💾 Actualizar Receta</button>
                                                        </form>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <script>
                function filtrarHistorial() {
                    let input = document.getElementById("buscadorHistorial").value.toLowerCase();
                    let filas = document.getElementsByClassName("fila-historial");
                    for (let i = 0; i < filas.length; i++) {
                        let texto = filas[i].querySelector(".nombre-dni").innerText.toLowerCase();
                        filas[i].style.display = texto.includes(input) ? "" : "none";
                    }
                }
            </script>
            {% endif %}

            {% if session['rol'] in ['administrador', 'secretaria', 'cajero'] %}
            <!-- PESTAÑA: FARMACIA & CAJA -->
            <div class="tab-pane fade" id="farmacia">
                <div class="row g-4">
                    <div class="col-md-4">
                        <div class="card-tech p-4 mb-4 border-info">
                            <h5 class="fw-bold text-info mb-3">📦 Nuevo Medicamento</h5>
                            <form action="/agregar_medicamento" method="POST">
                                <div class="mb-2"><input type="text" name="nombre" class="form-control" required placeholder="Nombre del Medicamento"></div>
                                <div class="mb-2"><textarea name="descripcion" class="form-control" rows="1" placeholder="Descripción / Presentación"></textarea></div>
                                <div class="row g-2 mb-3">
                                    <div class="col-md-6"><input type="number" name="stock" class="form-control" required placeholder="Stock" min="0"></div>
                                    <div class="col-md-6"><input type="number" step="0.01" name="precio" class="form-control" required placeholder="Precio S/" min="0"></div>
                                </div>
                                <button type="submit" class="btn btn-info text-white w-100 fw-bold rounded-3">➕ Registrar Medicamento</button>
                            </form>
                        </div>

                        <div class="card-tech p-4 border-warning">
                            <h5 class="fw-bold text-dark mb-3">🧾 Caja y Facturación</h5>
                            <form action="/facturar_transaccion" method="POST">
                                <div class="mb-2">
                                    <label class="form-label">Tipo de Transacción</label>
                                    <select name="tipo_transaccion" id="tipoTransaccion" class="form-select fw-bold text-primary" onchange="cambiarTipoTransaccion()" required>
                                        <option value="Medicamento">Venta de Medicamentos</option>
                                        <option value="Consulta">Cobro de Consulta / Cita Médica</option>
                                    </select>
                                </div>
                                <div class="mb-2"><input type="text" name="documento_cliente" class="form-control" required placeholder="DNI / RUC del Cliente"></div>
                                <div class="mb-3"><input type="text" name="cliente_nombre" class="form-control" required placeholder="Nombre / Razón Social"></div>
                                
                                <div id="seccionMedicamento">
                                    <div class="mb-2">
                                        <select name="medicamento_id" class="form-select">
                                            <option value="">-- Seleccionar Medicina --</option>
                                            {% for m in medicamentos %}
                                            <option value="{{ m.id }}">
                                                {{ m.nombre }} {% if m.descripcion %}({{ m.descripcion }}){% endif %} - Stock: {{ m.stock }} | S/ {{ "%.2f"|format(m.precio) }}
                                            </option>
                                            {% endfor %}
                                        </select>
                                    </div>
                                    <div class="mb-3"><input type="number" name="cantidad" class="form-control" placeholder="Cantidad" min="1" value="1"></div>
                                </div>

                                <div id="seccionConsulta" style="display: none;">
                                    <div class="mb-3">
                                        <label class="form-label text-danger">🩺 Seleccionar Cita Realizada (Pendientes de Cobro)</label>
                                        <select name="consulta_id" id="selectConsulta" class="form-select border-danger" onchange="autocompletarMedicoConsulta()">
                                            <option value="">-- Seleccionar Consulta / Paciente --</option>
                                            {% for cons in consultas %}
                                            <option value="{{ cons.id }}" data-medico-id="{{ cons.medico_id }}" data-medico-nombre="{{ cons.medico_nombre }}">
                                                {{ cons.fecha }} - Paciente: {{ cons.paciente_nombre }} (Dr/a. {{ cons.medico_nombre }})
                                            </option>
                                            {% endfor %}
                                        </select>
                                    </div>
                                    
                                    <div class="mb-3">
                                        <label class="form-label">👨‍⚕️ Médico Atendedor (Automático)</label>
                                        <input type="text" id="medicoNombreDisplay" class="form-control bg-light fw-bold text-secondary" readonly placeholder="Se autocompletará...">
                                        <input type="hidden" name="medico_id" id="medicoIdInput">
                                    </div>

                                    <div class="row g-2 mb-3">
                                        <div class="col-md-6">
                                            <label class="form-label text-primary">🏥 Monto Clínica (S/)</label>
                                            <input type="number" step="0.01" name="monto_clinica" id="montoClinica" class="form-control" placeholder="0.00" min="0" oninput="calcularTotalConsulta()">
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label text-success">👨‍⚕️ Monto Médico (S/)</label>
                                            <input type="number" step="0.01" name="monto_medico" id="montoMedico" class="form-control" placeholder="0.00" min="0" oninput="calcularTotalConsulta()">
                                        </div>
                                    </div>

                                    <div class="mb-3">
                                        <label class="form-label fw-bold text-dark">💰 Monto Total Consulta (S/)</label>
                                        <input type="number" step="0.01" id="montoTotalConsulta" class="form-control bg-light fw-bold fs-5 text-primary" readonly placeholder="0.00">
                                    </div>
                                </div>

                                <div class="mb-3">
                                    <select name="tipo_comprobante" class="form-select fw-semibold" required>
                                        <option value="Boleta">Boleta Electrónica</option><option value="Factura">Factura Electrónica</option>
                                    </select>
                                </div>
                                <button type="submit" class="btn btn-warning w-100 fw-bold rounded-3 text-dark py-2">💳 Procesar & Emitir Comprobante</button>
                            </form>
                        </div>
                    </div>

                    <script>
                        function cambiarTipoTransaccion() {
                            let tipo = document.getElementById("tipoTransaccion").value;
                            document.getElementById("seccionMedicamento").style.display = tipo === 'Medicamento' ? 'block' : 'none';
                            document.getElementById("seccionConsulta").style.display = tipo === 'Consulta' ? 'block' : 'none';
                        }
                        function autocompletarMedicoConsulta() {
                            let select = document.getElementById("selectConsulta");
                            let option = select.options[select.selectedIndex];
                            document.getElementById("medicoIdInput").value = option.getAttribute("data-medico-id") || "";
                            document.getElementById("medicoNombreDisplay").value = option.getAttribute("data-medico-nombre") ? "Dr/a. " + option.getAttribute("data-medico-nombre") : "";
                        }
                        function calcularTotalConsulta() {
                            let clinica = parseFloat(document.getElementById("montoClinica").value) || 0;
                            let medico = parseFloat(document.getElementById("montoMedico").value) || 0;
                            document.getElementById("montoTotalConsulta").value = (clinica + medico).toFixed(2);
                        }
                    </script>

                    <div class="col-md-8">
                        <div class="card-tech mb-4">
                            <div class="card-header-tech"><h5 class="fw-bold m-0">💊 Inventario Actual de Medicamentos</h5></div>
                            <div class="table-responsive" style="max-height: 250px; overflow-y: auto;">
                                <table class="table table-tech align-middle mb-0">
                                    <thead><tr><th>Medicamento</th><th>Descripción</th><th>Stock</th><th>Precio Unitario</th><th>Acción</th></tr></thead>
                                    <tbody>
                                        {% for med in medicamentos %}
                                        <tr>
                                            <td class="fw-bold text-dark">{{ med.nombre }}</td>
                                            <td><small class="text-muted">{{ med.descripcion or 'Sin descripción' }}</small></td>
                                            <td><span class="badge {{ 'badge-soft-success' if med.stock > 5 else 'badge-soft-danger' }}">{{ med.stock }} unidades</span></td>
                                            <td class="fw-bold text-primary">S/ {{ "%.2f"|format(med.precio) }}</td>
                                            <td><a href="/eliminar_medicamento/{{ med.id }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('¿Eliminar medicamento?');">🗑️</a></td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div class="card-tech">
                            <div class="card-header-tech"><h5 class="fw-bold m-0">📊 Historial de Transacciones y Caja</h5></div>
                            <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                                <table class="table table-tech align-middle mb-0">
                                    <thead><tr><th>Tipo / Comp.</th><th>Cliente</th><th>Detalle / Médico</th><th>Total / División</th><th>Acciones</th></tr></thead>
                                    <tbody>
                                        {% for v in ventas %}
                                        <tr>
                                            <td><span class="badge bg-secondary">{{ v.tipo_transaccion }}</span><br><small class="fw-bold text-primary">{{ v.tipo_comprobante }} N°{{ v.id }}</small></td>
                                            <td>{{ v.cliente_nombre }}<br><small class="text-muted">Doc: {{ v.documento_cliente }}</small></td>
                                            <td>
                                                {% if v.tipo_transaccion == 'Medicamento' %}
                                                    {{ v.medicamento }} (x{{ v.cantidad }})
                                                {% else %}
                                                    Dr/a. {{ v.medico_nombre or 'General' }}
                                                {% endif %}
                                            </td>
                                            <td>
                                                <span class="badge badge-soft-success fs-6">S/ {{ "%.2f"|format(v.total) }}</span>
                                                {% if v.tipo_transaccion == 'Consulta' %}
                                                <div class="small text-muted mt-1">🏥 Clínica: S/ {{ "%.2f"|format(v.monto_clinica) }}<br>👨‍⚕️ Médico: S/ {{ "%.2f"|format(v.monto_medico) }}</div>
                                                {% endif %}
                                            </td>
                                            <td>
                                                <div class="d-flex gap-1">
                                                    <a href="/descargar_recibo/{{ v.id }}" target="_blank" class="btn btn-sm btn-light border fw-bold" title="Descargar PDF">📄</a>
                                                    <a href="/eliminar_venta/{{ v.id }}" class="btn btn-sm btn-outline-danger fw-bold" onclick="return confirm('¿Eliminar este comprobante/venta? (Si es medicamento, retornará al stock)');" title="Eliminar Venta">🗑️</a>
                                                </div>
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {% endif %}

            {% if session['rol'] in ['administrador', 'secretaria', 'cajero'] %}
            <!-- PESTAÑA: REPORTES Y FINANZAS -->
            <div class="tab-pane fade" id="reportes">
                <div class="row g-4">
                    <div class="col-md-12">
                        <div class="card-tech p-4">
                            <div class="row align-items-center g-3">
                                <div class="col-md-4">
                                    <h5 class="fw-bold text-success m-0">📊 Panel Financiero & Gráficas</h5>
                                    <small class="text-muted">Filtre ingresos por calendario interactivo</small>
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label">Tipo de Vista</label>
                                    <select id="filtroModo" class="form-select fw-bold text-primary" onchange="cambiarModoFiltro()">
                                        <option value="dia">📅 Por Día (Calendario Diario)</option>
                                        <option value="mes">🗓️ Por Mes (Calendario Mensual)</option>
                                        <option value="ano">📈 Por Año (Selector Anual)</option>
                                    </select>
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label" id="labelSelectorFecha">Seleccionar Fecha / Periodo</label>
                                    <input type="date" id="inputDia" class="form-control selector-fecha" onchange="filtrarGrafica()">
                                    <input type="month" id="inputMes" class="form-control selector-fecha" style="display:none;" onchange="filtrarGrafica()">
                                    <select id="inputAno" class="form-select selector-fecha" style="display:none;" onchange="filtrarGrafica()">
                                        {% for r in rep_anos %}<option value="{{ r.periodo }}">{{ r.periodo }}</option>{% endfor %}
                                    </select>
                                </div>
                                <div class="col-md-2 text-end">
                                    <button class="btn btn-outline-secondary btn-sm fw-bold mt-4" onclick="resetFiltros()">🔄 Ver Todo</button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-12">
                        <div class="card-tech p-4">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h6 class="fw-bold text-dark m-0">📈 Comparativa de Ingresos: Clínica vs Médicos (Gráfica Horizontal)</h6>
                                <span class="badge badge-soft-primary" id="lblPeriodoActivo">Todos los Registros</span>
                            </div>
                            <div style="position: relative; height: 260px; width: 100%;">
                                <canvas id="graficaHorizontalIngresos"></canvas>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-12">
                        <div class="card-tech p-4">
                            <h6 class="fw-bold text-secondary mb-3">📋 Resumen Detallado de Ingresos</h6>
                            <div class="table-responsive">
                                <table class="table table-tech align-middle mb-0" id="tablaReportesDetalle">
                                    <thead><tr><th>Periodo</th><th>Total Ingresos</th><th>🏥 Clínica</th><th>👨‍⚕️ Médicos</th></tr></thead>
                                    <tbody id="tbodyReportes">
                                        {% for r in rep_dias %}
                                        <tr data-periodo="{{ r.periodo }}" data-tipo="dia" data-total="{{ r.total_ingresos }}" data-clinica="{{ r.total_clinica }}" data-medicos="{{ r.total_medicos }}">
                                            <td class="fw-bold text-primary">{{ r.periodo }}</td>
                                            <td class="fw-bold text-dark">S/ {{ "%.2f"|format(r.total_ingresos) }}</td>
                                            <td class="text-info fw-semibold">S/ {{ "%.2f"|format(r.total_clinica) }}</td>
                                            <td class="text-success fw-semibold">S/ {{ "%.2f"|format(r.total_medicos) }}</td>
                                        </tr>
                                        {% endfor %}
                                        {% for r in rep_meses %}
                                        <tr data-periodo="{{ r.periodo }}" data-tipo="mes" data-total="{{ r.total_ingresos }}" data-clinica="{{ r.total_clinica }}" data-medicos="{{ r.total_medicos }}" style="display:none;">
                                            <td class="fw-bold text-primary">{{ r.periodo }}</td>
                                            <td class="fw-bold text-dark">S/ {{ "%.2f"|format(r.total_ingresos) }}</td>
                                            <td class="text-info fw-semibold">S/ {{ "%.2f"|format(r.total_clinica) }}</td>
                                            <td class="text-success fw-semibold">S/ {{ "%.2f"|format(r.total_medicos) }}</td>
                                        </tr>
                                        {% endfor %}
                                        {% for r in rep_anos %}
                                        <tr data-periodo="{{ r.periodo }}" data-tipo="ano" data-total="{{ r.total_ingresos }}" data-clinica="{{ r.total_clinica }}" data-medicos="{{ r.total_medicos }}" style="display:none;">
                                            <td class="fw-bold text-primary">{{ r.periodo }}</td>
                                            <td class="fw-bold text-dark">S/ {{ "%.2f"|format(r.total_ingresos) }}</td>
                                            <td class="text-info fw-semibold">S/ {{ "%.2f"|format(r.total_clinica) }}</td>
                                            <td class="text-success fw-semibold">S/ {{ "%.2f"|format(r.total_medicos) }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                let chartHorizontal;
                document.addEventListener("DOMContentLoaded", function() {
                    inicializarGraficaHorizontal([0], [0], ['Sin Datos']);
                    filtrarGrafica();
                });
                function cambiarModoFiltro() {
                    let modo = document.getElementById("filtroModo").value;
                    document.getElementById("inputDia").style.display = modo === 'dia' ? 'block' : 'none';
                    document.getElementById("inputMes").style.display = modo === 'mes' ? 'block' : 'none';
                    document.getElementById("inputAno").style.display = modo === 'ano' ? 'block' : 'none';
                    document.querySelectorAll("#tbodyReportes tr").forEach(f => {
                        f.style.display = f.getAttribute("data-tipo") === modo ? "" : "none";
                    });
                    filtrarGrafica();
                }
                function inicializarGraficaHorizontal(clinicaData, medicosData, labels) {
                    const ctx = document.getElementById('graficaHorizontalIngresos').getContext('2d');
                    if (chartHorizontal) { chartHorizontal.destroy(); }
                    chartHorizontal = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [
                                { label: '🏥 Clínica (S/)', data: clinicaData, backgroundColor: '#0284c7', borderRadius: 8 },
                                { label: '👨‍⚕️ Médicos (S/)', data: medicosData, backgroundColor: '#10b981', borderRadius: 8 }
                            ]
                        },
                        options: {
                            indexAxis: 'y',
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: { x: { beginAtZero: true, grid: { color: '#f1f5f9' } }, y: { grid: { display: false } } }
                        }
                    });
                }
                function filtrarGrafica() {
                    let modo = document.getElementById("filtroModo").value;
                    let valorFiltro = modo === 'dia' ? document.getElementById("inputDia").value : (modo === 'mes' ? document.getElementById("inputMes").value : document.getElementById("inputAno").value);
                    let clinicaVals = [], medicosVals = [], labelPeriodos = [];
                    document.querySelectorAll("#tbodyReportes tr").forEach(f => {
                        if(f.getAttribute("data-tipo") === modo) {
                            let periodo = f.getAttribute("data-periodo");
                            if(!valorFiltro || periodo === valorFiltro) {
                                labelPeriodos.push(periodo);
                                clinicaVals.push(parseFloat(f.getAttribute("data-clinica")));
                                medicosVals.push(parseFloat(f.getAttribute("data-medicos")));
                            }
                        }
                    });
                    if(labelPeriodos.length === 0) { labelPeriodos = [valorFiltro || 'Seleccione Fecha']; clinicaVals = [0]; medicosVals = [0]; }
                    document.getElementById("lblPeriodoActivo").innerText = valorFiltro ? "Filtro: " + valorFiltro : "Vista General (" + modo.toUpperCase() + ")";
                    inicializarGraficaHorizontal(clinicaVals, medicosVals, labelPeriodos);
                }
                function resetFiltros() {
                    document.getElementById("inputDia").value = "";
                    document.getElementById("inputMes").value = "";
                    filtrarGrafica();
                }
            </script>
            {% endif %}

            {% if session['rol'] == 'administrador' %}
            <!-- PESTAÑA: MÉDICOS Y USUARIOS -->
            <div class="tab-pane fade" id="medicos">
                <div class="row g-4">
                    <div class="col-md-5">
                        <div class="card-tech p-4 mb-4">
                            <h5 class="fw-bold text-info mb-3">1. Especialidades</h5>
                            <form action="/agregar_especialidad" method="POST" class="d-flex gap-2">
                                <input type="text" name="nombre" class="form-control" required placeholder="Ej. Gastroenterología">
                                <button type="submit" class="btn btn-info text-white fw-bold">Guardar</button>
                            </form>
                        </div>
                        <div class="card-tech p-4">
                            <h5 class="fw-bold text-secondary mb-3">Especialidades</h5>
                            <ul class="list-group list-group-flush">
                                {% for e in especialidades %}
                                <li class="list-group-item d-flex justify-content-between align-items-center bg-transparent">
                                    {{ e.nombre }}
                                    <a href="/eliminar_especialidad/{{ e.id }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('¿Eliminar?');">🗑️</a>
                                </li>
                                {% endfor %}
                            </ul>
                        </div>
                    </div>
                    <div class="col-md-7">
                        <div class="card-tech p-4 mb-4">
                            <h5 class="fw-bold text-primary mb-3">2. Nuevo Médico</h5>
                            <form action="/agregar_medico" method="POST">
                                <div class="row g-2 mb-3">
                                    <div class="col-md-6"><input type="text" name="nombre" class="form-control" required placeholder="Nombre Completo"></div>
                                    <div class="col-md-6"><input type="text" name="dni" class="form-control" required placeholder="DNI"></div>
                                    <div class="col-md-6"><input type="text" name="cmp" class="form-control" required placeholder="CMP"></div>
                                    <div class="col-md-6">
                                        <select name="especialidad_id" class="form-select" required>
                                            <option value="">-- Especialidad --</option>
                                            {% for e in especialidades %}<option value="{{ e.id }}">{{ e.nombre }}</option>{% endfor %}
                                        </select>
                                    </div>
                                </div>
                                <button type="submit" class="btn btn-primary w-100 fw-bold">👨‍⚕️ Registrar Médico o Especialista</button>
                            </form>
                        </div>
                        <div class="card-tech p-4">
                            <h5 class="fw-bold text-secondary mb-3">👨‍⚕️ Staff Médico</h5>
                            <div class="table-responsive">
                                <table class="table table-tech align-middle mb-0">
                                    <thead><tr><th>CMP</th><th>Médico / DNI</th><th>Especialidad</th><th>Acción</th></tr></thead>
                                    <tbody>
                                        {% for m in medicos %}
                                        <tr>
                                            <td><span class="badge bg-dark">CMP {{ m.cmp }}</span></td>
                                            <td><div class="fw-bold text-primary">{{ m.nombre }}</div><small class="text-muted">DNI: {{ m.dni }}</small></td>
                                            <td><span class="badge bg-info text-dark">{{ m.especialidad }}</span></td>
                                            <td><a href="/eliminar_medico/{{ m.id }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('¿Eliminar?');">🗑️</a></td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="tab-pane fade" id="usuarios">
                <div class="row g-4">
                    <div class="col-md-4">
                        <div class="card-tech p-4">
                            <h5 class="fw-bold text-warning mb-3">Crear Usuario</h5>
                            <form action="/agregar_usuario" method="POST">
                                <div class="mb-2"><input type="text" name="nombres" class="form-control" required placeholder="Nombres Completos"></div>
                                <div class="mb-2"><input type="text" name="dni" class="form-control" required placeholder="DNI"></div>
                                <div class="mb-2"><input type="text" name="username" class="form-control" required placeholder="Usuario (Login)"></div>
                                <div class="mb-2"><input type="password" name="password" class="form-control" required placeholder="Contraseña"></div>
                                <div class="mb-3">
                                    <select name="rol" class="form-select" required>
                                        <option value="administrador">Administrador</option>
                                        <option value="secretaria">Secretaria</option>
                                    </select>
                                </div>
                                <button type="submit" class="btn btn-warning w-100 fw-bold text-dark">💾 Guardar</button>
                            </form>
                        </div>
                    </div>
                    <div class="col-md-8">
                        <div class="card-tech">
                            <div class="card-header-tech"><h5 class="fw-bold m-0">👥 Usuarios del Sistema</h5></div>
                            <div class="table-responsive">
                                <table class="table table-tech align-middle mb-0">
                                    <thead><tr><th>ID</th><th>Personal / DNI</th><th>Usuario</th><th>Clave</th><th>Rol</th><th>Acción</th></tr></thead>
                                    <tbody>
                                        {% for u in usuarios %}
                                        <tr>
                                            <td>#{{ u.id }}</td>
                                            <td><div class="fw-bold">{{ u.nombres }}</div><small class="text-muted">DNI: {{ u.dni }}</small></td>
                                            <td class="fw-bold text-primary">{{ u.username }}</td>
                                            <td><code>{{ u.password }}</code></td>
                                            <td><span class="badge bg-secondary">{{ u.rol|capitalize }}</span></td>
                                            <td>
                                                {% if u.id != session['usuario_id'] %}
                                                <a href="/eliminar_usuario/{{ u.id }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('¿Eliminar?');">🗑️</a>
                                                {% endif %}
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {% endif %}

        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            let activeTab = localStorage.getItem('activeTabClinica');
            if(activeTab){
                let tabElement = document.querySelector('button[data-bs-target="' + activeTab + '"]');
                if(tabElement) { new bootstrap.Tab(tabElement).show(); }
            }
            document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(function(tab) {
                tab.addEventListener('shown.bs.tab', function (event) {
                    localStorage.setItem('activeTabClinica', event.target.dataset.bsTarget);
                });
            });
        });
    </script>
</body>
</html>
"""

# --- RUTAS DE APLICACIÓN ---
@app.route('/logo_clinica')
def servir_logo():
    try: return send_file('526422900_774722791753650_413711329622849230_n.jpg')
    except Exception as e: return f"Imagen no encontrada", 404

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario_id' in session: return redirect('/')
    if request.method == 'POST':
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (request.form['username'], request.form['password']))
        usuario = cursor.fetchone()
        conexion.close()
        if usuario:
            session['usuario_id'] = dict(usuario)['id']
            session['username'] = dict(usuario)['username']
            session['rol'] = dict(usuario)['rol']
            return redirect('/')
        else: flash("Usuario o contraseña incorrectos")
    return render_template_string(HTML_LOGIN)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
@login_requerido
def inicio():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT * FROM pacientes ORDER BY id DESC")
    pacientes = cursor.fetchall()
    
    cursor.execute("SELECT m.id, m.nombre, m.dni, m.cmp, e.nombre as especialidad FROM medicos m LEFT JOIN especialidades e ON m.especialidad_id = e.id ORDER BY m.nombre ASC")
    medicos = cursor.fetchall()
    
    query_citas = """
        SELECT c.id, c.fecha, c.estado, c.tipo_atencion, c.medico_id,
               p.nombre as paciente_nombre, p.dni as paciente_dni, p.motivo_consulta, p.antecedentes, p.diagnosticos, p.alergias, p.grupo_sanguineo, p.estatura, p.peso,
               m.nombre as medico_nombre, e.nombre as especialidad
        FROM citas c 
        JOIN pacientes p ON c.paciente_id = p.id 
        LEFT JOIN medicos m ON c.medico_id = m.id
        LEFT JOIN especialidades e ON m.especialidad_id = e.id
        WHERE c.estado = 'pendiente' ORDER BY c.fecha ASC
    """
    cursor.execute(query_citas)
    citas = cursor.fetchall()
    
    query_triajes = """
        SELECT t.*, c.fecha, p.nombre as paciente_nombre, m.nombre as medico_nombre
        FROM triajes t
        JOIN citas c ON t.cita_id = c.id
        JOIN pacientes p ON c.paciente_id = p.id
        LEFT JOIN medicos m ON c.medico_id = m.id
        ORDER BY t.id DESC
    """
    cursor.execute(query_triajes)
    triajes = cursor.fetchall()
    
    query_consultas = """
        SELECT cons.id, cons.diagnostico, cons.medicina, cons.frecuencia, cons.cantidad, cons.tipo_atencion,
               c.fecha, p.nombre as paciente_nombre, p.dni as paciente_dni,
               m.id as medico_id, m.nombre as medico_nombre
        FROM consultas cons 
        JOIN citas c ON cons.cita_id = c.id 
        JOIN pacientes p ON c.paciente_id = p.id
        LEFT JOIN medicos m ON c.medico_id = m.id
        WHERE cons.tipo_atencion != 'Control' 
          AND cons.id NOT IN (SELECT COALESCE(consulta_id, 0) FROM ventas WHERE consulta_id IS NOT NULL)
        ORDER BY cons.id DESC
    """
    cursor.execute(query_consultas)
    consultas = cursor.fetchall()
    
    cursor.execute("SELECT * FROM medicamentos ORDER BY nombre ASC")
    medicamentos = cursor.fetchall()
    
    query_ventas = """
        SELECT v.*, m.nombre AS medicamento, m.descripcion AS descripcion_med, med.nombre AS medico_nombre 
        FROM ventas v 
        LEFT JOIN medicamentos m ON v.medicamento_id = m.id 
        LEFT JOIN medicos med ON v.medico_id = med.id 
        ORDER BY v.id DESC LIMIT 15
    """
    cursor.execute(query_ventas)
    ventas = cursor.fetchall()
    
    cursor.execute("""
        SELECT SUBSTR(fecha, 1, 10) as periodo, 
               SUM(total) as total_ingresos, 
               SUM(CASE WHEN tipo_transaccion='Medicamento' THEN total ELSE monto_clinica END) as total_clinica,
               SUM(CASE WHEN tipo_transaccion='Medicamento' THEN 0 ELSE monto_medico END) as total_medicos
        FROM ventas GROUP BY SUBSTR(fecha, 1, 10) ORDER BY periodo DESC
    """)
    rep_dias = cursor.fetchall()

    cursor.execute("""
        SELECT SUBSTR(fecha, 1, 7) as periodo, 
               SUM(total) as total_ingresos, 
               SUM(CASE WHEN tipo_transaccion='Medicamento' THEN total ELSE monto_clinica END) as total_clinica,
               SUM(CASE WHEN tipo_transaccion='Medicamento' THEN 0 ELSE monto_medico END) as total_medicos
        FROM ventas GROUP BY SUBSTR(fecha, 1, 7) ORDER BY periodo DESC
    """)
    rep_meses = cursor.fetchall()

    cursor.execute("""
        SELECT SUBSTR(fecha, 1, 4) as periodo, 
               SUM(total) as total_ingresos, 
               SUM(CASE WHEN tipo_transaccion='Medicamento' THEN total ELSE monto_clinica END) as total_clinica,
               SUM(CASE WHEN tipo_transaccion='Medicamento' THEN 0 ELSE monto_medico END) as total_medicos
        FROM ventas GROUP BY SUBSTR(fecha, 1, 4) ORDER BY periodo DESC
    """)
    rep_anos = cursor.fetchall()
    
    usuarios, especialidades = [], []
    cursor.execute("SELECT * FROM usuarios ORDER BY id ASC")
    usuarios = cursor.fetchall()
    cursor.execute("SELECT * FROM especialidades ORDER BY nombre ASC")
    especialidades = cursor.fetchall()
        
    conexion.close()
    return render_template_string(HTML_TEMPLATE, pacientes=pacientes, citas=citas, triajes=triajes, consultas=consultas, medicamentos=medicamentos, ventas=ventas, usuarios=usuarios, especialidades=especialidades, medicos=medicos, rep_dias=rep_dias, rep_meses=rep_meses, rep_anos=rep_anos)

@app.route('/agregar_paciente', methods=['POST'])
@login_requerido
def agregar_paciente():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    query = "INSERT INTO pacientes (nombre, dni, sexo, fecha_nacimiento, direccion, celular, motivo_consulta, antecedentes, diagnosticos, alergias, grupo_sanguineo, estatura, peso) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    
    estatura_val = float(request.form.get('estatura') or 0)
    peso_val = float(request.form.get('peso') or 0)
    
    valores = (
        request.form['nombre'], 
        request.form['dni'], 
        request.form.get('sexo', ''), 
        request.form.get('fecha_nacimiento', ''), 
        request.form.get('direccion', ''), 
        request.form.get('celular', ''), 
        request.form.get('motivo_consulta', ''), 
        request.form.get('antecedentes', ''), 
        request.form.get('diagnosticos', ''), 
        request.form.get('alergias', ''), 
        request.form.get('grupo_sanguineo', 'Desconoce'),
        estatura_val,
        peso_val
    )
    try:
        cursor.execute(query, valores)
        conexion.commit(); flash("✅ Ficha Médica creada exitosamente.")
    except sqlite3.IntegrityError: flash(f"❌ Error: El DNI ya está registrado.")
    finally: conexion.close()
    return redirect('/')

@app.route('/editar_paciente/<int:paciente_id>', methods=['POST'])
@login_requerido
def editar_paciente(paciente_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            UPDATE pacientes SET nombre=?, dni=?, sexo=?, fecha_nacimiento=?, direccion=?, celular=?, 
                                 motivo_consulta=?, antecedentes=?, diagnosticos=?, alergias=?, grupo_sanguineo=?, estatura=?, peso=?
            WHERE id=?
        """, (
            request.form['nombre'], request.form['dni'], request.form['sexo'], request.form['fecha_nacimiento'],
            request.form['direccion'], request.form['celular'], request.form['motivo_consulta'],
            request.form['antecedentes'], request.form['diagnosticos'], request.form['alergias'],
            request.form['grupo_sanguineo'], float(request.form['estatura'] or 0), float(request.form['peso'] or 0),
            paciente_id
        ))
        conexion.commit()
        flash("✅ Ficha de paciente actualizada correctamente.")
    except Exception as e:
        flash(f"❌ Error al actualizar paciente: {e}")
    finally:
        conexion.close()
    return redirect('/')

@app.route('/agendar_cita', methods=['POST'])
@login_requerido
def agendar_cita():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    tipo_atencion = request.form.get('tipo_atencion', 'Cita')
    
    fecha_f = request.form['fecha_cita']
    hora_f = request.form['hora_cita']
    minuto_f = request.form['minuto_cita']
    fecha_hora_completa = f"{fecha_f} {hora_f}:{minuto_f}:00"
    
    cursor.execute("INSERT INTO citas (paciente_id, medico_id, fecha, tipo_atencion) VALUES (?, ?, ?, ?)", 
                   (request.form['paciente_id'], request.form['medico_id'], fecha_hora_completa, tipo_atencion))
    conexion.commit(); conexion.close(); flash(f"✅ {tipo_atencion} agendada correctamente.")
    return redirect('/')

@app.route('/editar_cita/<int:cita_id>', methods=['POST'])
@login_requerido
def editar_cita(cita_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE citas SET tipo_atencion=?, medico_id=?, fecha=? WHERE id=?
    """, (request.form['tipo_atencion'], request.form['medico_id'], request.form['fecha'], cita_id))
    conexion.commit()
    conexion.close()
    flash("✅ Cita/Control actualizado correctamente.")
    return redirect('/')

@app.route('/eliminar_cita/<int:cita_id>')
@login_requerido
def eliminar_cita(cita_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM citas WHERE id = ?", (cita_id,))
    conexion.commit()
    conexion.close()
    flash("✅ Cita eliminada correctamente.")
    return redirect('/')

@app.route('/registrar_triaje', methods=['POST'])
@login_requerido
def registrar_triaje():
    cita_id = request.form['cita_id']
    presion = request.form['presion_arterial']
    temperatura = float(request.form['temperatura'] or 0)
    saturacion = int(request.form['saturacion'] or 0)
    latidos = int(request.form['latidos'] or 0)
    frecuencia_resp = int(request.form['frecuencia_respiratoria'] or 0)
    peso = float(request.form['peso'] or 0)
    talla = float(request.form['talla'] or 0)
    imc = peso / (talla * talla) if talla > 0 else 0
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            INSERT INTO triajes (cita_id, presion_arterial, temperatura, saturacion, latidos, frecuencia_respiratoria, peso, talla, imc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cita_id, presion, temperatura, saturacion, latidos, frecuencia_resp, peso, talla, imc))
        conexion.commit()
        flash("✅ Signos vitales y triaje registrados correctamente.")
    except sqlite3.IntegrityError:
        flash("❌ Error: Ya existe un registro de triaje para esta cita.")
    finally:
        conexion.close()
    return redirect('/')

@app.route('/editar_triaje/<int:triaje_id>', methods=['POST'])
@login_requerido
def editar_triaje(triaje_id):
    peso = float(request.form['peso'] or 0)
    talla = float(request.form['talla'] or 0)
    imc = peso / (talla * talla) if talla > 0 else 0
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE triajes SET presion_arterial=?, temperatura=?, saturacion=?, latidos=?, frecuencia_respiratoria=?, peso=?, talla=?, imc=?
        WHERE id=?
    """, (
        request.form['presion_arterial'], float(request.form['temperatura'] or 0),
        int(request.form['saturacion'] or 0), int(request.form['latidos'] or 0),
        int(request.form['frecuencia_respiratoria'] or 0), peso, talla, imc, triaje_id
    ))
    conexion.commit()
    conexion.close()
    flash("✅ Triaje actualizado correctamente.")
    return redirect('/')

@app.route('/registrar_consulta', methods=['POST'])
@login_requerido
def registrar_consulta():
    cita_id = request.form['cita_id']
    diagnostico = request.form['diagnostico']
    medicina = request.form.get('medicina', '')
    frecuencia = request.form.get('frecuencia', '')
    cantidad = request.form.get('cantidad', '')
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT tipo_atencion FROM citas WHERE id = ?", (cita_id,))
    cita_data = cursor.fetchone()
    tipo_atencion = cita_data['tipo_atencion'] if cita_data else 'Consulta'
    
    cursor.execute("INSERT INTO consultas (cita_id, diagnostico, medicina, frecuencia, cantidad, tipo_atencion) VALUES (?, ?, ?, ?, ?, ?)", 
                   (cita_id, diagnostico, medicina, frecuencia, cantidad, tipo_atencion))
    cursor.execute("UPDATE citas SET estado = 'completada' WHERE id = ?", (cita_id,))
    conexion.commit()
    consulta_id = cursor.lastrowid
    conexion.close()
    flash(f"✅ {tipo_atencion} registrada e integrada en la Historia Clínica. <a href='/descargar_receta/{consulta_id}' target='_blank' class='btn btn-primary btn-sm ms-3 fw-bold'>📄 Imprimir Reporte / Receta</a>")
    return redirect('/')

@app.route('/editar_consulta/<int:consulta_id>', methods=['POST'])
@login_requerido
def editar_consulta(consulta_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE consultas SET diagnostico=?, medicina=?, frecuencia=?, cantidad=? WHERE id=?
    """, (
        request.form['diagnostico'], request.form.get('medicina', ''),
        request.form.get('frecuencia', ''), request.form.get('cantidad', ''), consulta_id
    ))
    conexion.commit()
    conexion.close()
    flash("✅ Receta / Consulta actualizada correctamente.")
    return redirect('/')

@app.route('/agregar_medicamento', methods=['POST'])
@login_requerido
def agregar_medicamento():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("INSERT INTO medicamentos (nombre, descripcion, stock, precio) VALUES (?, ?, ?, ?)", 
                       (request.form['nombre'], request.form.get('descripcion', ''), int(request.form['stock']), float(request.form['precio'])))
        conexion.commit(); flash("✅ Medicamento registrado en el inventario.")
    except Exception as e: flash(f"❌ Error al registrar medicamento: {e}")
    finally: conexion.close()
    return redirect('/')

@app.route('/eliminar_medicamento/<int:id_med>')
@login_requerido
def eliminar_medicamento(id_med):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM medicamentos WHERE id = ?", (id_med,))
    conexion.commit(); conexion.close(); flash("✅ Medicamento eliminado del inventario.")
    return redirect('/')

@app.route('/facturar_transaccion', methods=['POST'])
@login_requerido
def facturar_transaccion():
    tipo = request.form['tipo_transaccion']
    doc = request.form['documento_cliente']
    nombre_cliente = request.form['cliente_nombre']
    comprobante = request.form['tipo_comprobante']
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    if tipo == 'Medicamento':
        med_id = request.form['medicamento_id']
        cant = int(request.form['cantidad'])
        cursor.execute("SELECT nombre, stock, precio FROM medicamentos WHERE id = ?", (med_id,))
        med = cursor.fetchone()
        if med and med['stock'] >= cant:
            total = med['precio'] * cant
            cursor.execute("INSERT INTO ventas (tipo_transaccion, medicamento_id, cantidad, total, tipo_comprobante, documento_cliente, cliente_nombre) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                           ('Medicamento', med_id, cant, total, comprobante, doc, nombre_cliente))
            cursor.execute("UPDATE medicamentos SET stock = stock - ? WHERE id = ?", (cant, med_id))
            conexion.commit(); flash("✅ Venta de medicamento facturada con éxito.")
        else: flash("❌ Error: Stock insuficiente o medicamento no seleccionado.")
    elif tipo == 'Consulta':
        consulta_id = request.form['consulta_id']
        medico_id = request.form['medico_id']
        monto_clinica = float(request.form['monto_clinica'] or 0)
        monto_medico = float(request.form['monto_medico'] or 0)
        monto_total = monto_clinica + monto_medico
        
        cursor.execute("INSERT INTO ventas (tipo_transaccion, total, monto_clinica, monto_medico, medico_id, consulta_id, tipo_comprobante, documento_cliente, cliente_nombre) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       ('Consulta', monto_total, monto_clinica, monto_medico, medico_id, consulta_id, comprobante, doc, nombre_cliente))
        conexion.commit(); flash(f"✅ Consulta cobrada. Total: S/ {monto_total:.2f} (Clínica: S/ {monto_clinica:.2f} | Médico: S/ {monto_medico:.2f})")
        
    conexion.close()
    return redirect('/')

@app.route('/eliminar_venta/<int:venta_id>')
@login_requerido
def eliminar_venta(venta_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,))
    venta = cursor.fetchone()
    if venta:
        if venta['tipo_transaccion'] == 'Medicamento' and venta['medicamento_id']:
            cursor.execute("UPDATE medicamentos SET stock = stock + ? WHERE id = ?", (venta['cantidad'], venta['medicamento_id']))
        cursor.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))
        conexion.commit()
        flash("✅ Comprobante eliminado correctamente (Stock restaurado si era medicamento).")
    conexion.close()
    return redirect('/')

@app.route('/descargar_recibo/<int:venta_id>')
@login_requerido
def descargar_recibo(venta_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT v.*, m.nombre AS medicamento, m.descripcion AS descripcion_med, med.nombre AS medico_nombre 
        FROM ventas v 
        LEFT JOIN medicamentos m ON v.medicamento_id = m.id 
        LEFT JOIN medicos med ON v.medico_id = med.id 
        WHERE v.id = ?
    """, (venta_id,))
    venta = cursor.fetchone()
    conexion.close()
    if not venta: return "Comprobante no encontrado", 404
    
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image('526422900_774722791753650_413711329622849230_n.jpg', x=10, y=8, w=35)
    except: pass
    pdf.set_font("Arial", 'B', 20); pdf.cell(200, 10, txt="GASTROCLINIC", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12); pdf.cell(200, 10, txt=f"{venta['tipo_comprobante'].upper()} ELECTRONICA - {venta['tipo_transaccion'].upper()}", ln=True, align='C')
    pdf.line(10, 35, 200, 35); pdf.ln(10)
    pdf.set_font("Arial", size=10); pdf.cell(200, 8, txt=f"Cliente: {venta['cliente_nombre']} - Doc: {venta['documento_cliente']}", ln=True)
    pdf.cell(200, 8, txt=f"Fecha: {venta['fecha']}", ln=True); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10); pdf.cell(100, 8, "Concepto / Detalle", border=1); pdf.cell(40, 8, "Tipo", border=1, align='C'); pdf.cell(50, 8, "Total", border=1, align='C'); pdf.ln(8)
    pdf.set_font("Arial", size=10)
    if venta['tipo_transaccion'] == 'Medicamento':
        desc = f" ({venta['descripcion_med']})" if venta['descripcion_med'] else ""
        concepto = f"{venta['medicamento']}{desc} (x{venta['cantidad']})"
    else:
        concepto = f"Atencion Medica - Dr/a. {venta['medico_nombre']}"
        
    pdf.cell(100, 8, str(concepto), border=1); pdf.cell(40, 8, str(venta['tipo_transaccion']), border=1, align='C'); pdf.cell(50, 8, f"S/{venta['total']:.2f}", border=1, align='C')
    
    nombre = f"comprobante_{venta['id']}.pdf"; pdf.output(nombre)
    return send_file(nombre, as_attachment=True)

@app.route('/descargar_historia_paciente/<int:paciente_id>')
@login_requerido
def descargar_historia_paciente(paciente_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM pacientes WHERE id = ?", (paciente_id,))
    paciente = cursor.fetchone()
    
    query_historial = """
        SELECT cons.id, cons.diagnostico, cons.medicina, cons.frecuencia, cons.cantidad, cons.tipo_atencion,
               c.fecha, m.nombre as medico_nombre, e.nombre as especialidad,
               t.presion_arterial, t.temperatura, t.saturacion, t.latidos, t.frecuencia_respiratoria, t.peso as triaje_peso, t.talla as triaje_talla, t.imc
        FROM consultas cons
        JOIN citas c ON cons.cita_id = c.id
        LEFT JOIN medicos m ON c.medico_id = m.id
        LEFT JOIN especialidades e ON m.especialidad_id = e.id
        LEFT JOIN triajes t ON t.cita_id = c.id
        WHERE c.paciente_id = ?
        ORDER BY c.fecha DESC
    """
    cursor.execute(query_historial, (paciente_id,))
    historial = cursor.fetchall()
    conexion.close()
    if not paciente: return "Paciente no encontrado", 404
    
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image('526422900_774722791753650_413711329622849230_n.jpg', x=15, y=10, w=35)
    except: pass
    pdf.set_y(15)
    pdf.set_font("Arial", 'B', 22); pdf.cell(200, 10, txt="GASTROCLINIC", ln=True, align='C')
    pdf.set_font("Arial", 'B', 13); pdf.cell(200, 8, txt="HISTORIA CLINICA GENERAL DEL PACIENTE", ln=True, align='C')
    pdf.line(10, 38, 200, 38); pdf.ln(12)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(200, 8, txt="1. DATOS PERSONALES", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Nombre:"); pdf.set_font("Arial", '', 10); pdf.cell(100, 6, txt=f"{paciente['nombre']}", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="DNI:"); pdf.set_font("Arial", '', 10); pdf.cell(60, 6, txt=f"{paciente['dni']}")
    pdf.set_font("Arial", 'B', 10); pdf.cell(25, 6, txt="Sexo:"); pdf.set_font("Arial", '', 10); pdf.cell(50, 6, txt=f"{paciente['sexo']}", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="F. Nacimiento:"); pdf.set_font("Arial", '', 10); pdf.cell(60, 6, txt=f"{paciente['fecha_nacimiento']}")
    pdf.set_font("Arial", 'B', 10); pdf.cell(25, 6, txt="Celular:"); pdf.set_font("Arial", '', 10); pdf.cell(50, 6, txt=f"{paciente['celular'] or 'No registrado'}", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Direccion:"); pdf.set_font("Arial", '', 10); pdf.cell(150, 6, txt=f"{paciente['direccion'] or 'No registrada'}", ln=True)
    pdf.ln(3)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(200, 8, txt="2. PERFIL CLINICO Y ANTROPOMETRIA BASE", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Grupo Sanguineo:"); pdf.set_font("Arial", '', 10); pdf.cell(60, 6, txt=f"{paciente['grupo_sanguineo'] or 'Desconoce'}")
    pdf.set_font("Arial", 'B', 10); pdf.cell(25, 6, txt="Estatura:"); pdf.set_font("Arial", '', 10); pdf.cell(30, 6, txt=f"{paciente['estatura']} m", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Peso:"); pdf.set_font("Arial", '', 10); pdf.cell(60, 6, txt=f"{paciente['peso']} kg", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Alergias:"); pdf.set_font("Arial", '', 10); pdf.cell(150, 6, txt=f"{paciente['alergias'] or 'Ninguna'}", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Motivo Consulta:"); pdf.set_font("Arial", '', 10); pdf.multi_cell(150, 6, txt=f"{paciente['motivo_consulta'] or 'Ninguno'}")
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Antecedentes:"); pdf.set_font("Arial", '', 10); pdf.multi_cell(150, 6, txt=f"{paciente['antecedentes'] or 'Ninguno'}")
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Diagnosticos Prev.:"); pdf.set_font("Arial", '', 10); pdf.multi_cell(150, 6, txt=f"{paciente['diagnosticos'] or 'Ninguno'}")
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(200, 8, txt="3. REGISTRO DE TRIAJE, ATENCIONES Y CONTROLES", ln=True)
    if not historial:
        pdf.set_font("Arial", 'I', 10); pdf.cell(200, 6, txt="No hay atenciones o controles registrados para este paciente.", ln=True)
    else:
        for h in historial:
            tipo_label = h['tipo_atencion'] if 'tipo_atencion' in h.keys() else 'Consulta'
            pdf.set_font("Arial", 'B', 10); pdf.cell(30, 6, txt="Fecha/Tipo:"); pdf.set_font("Arial", '', 10); pdf.cell(160, 6, txt=f"{h['fecha']} [{tipo_label.upper()}] (Dr/a. {h['medico_nombre']} - {h['especialidad']})", ln=True)
            if h['presion_arterial']:
                pdf.set_font("Arial", 'B', 9); pdf.cell(30, 5, txt="Triaje (Signos):"); pdf.set_font("Arial", '', 9); pdf.cell(160, 5, txt=f"P.A: {h['presion_arterial']} | Temp: {h['temperatura']}C | Sat O2: {h['saturacion']}% | Pulso: {h['latidos']} lpm | Resp: {h['frecuencia_respiratoria']} rpm", ln=True)
                pdf.set_font("Arial", 'B', 9); pdf.cell(30, 5, txt="Antropometría:"); pdf.set_font("Arial", '', 9); pdf.cell(160, 5, txt=f"Peso: {h['triaje_peso']} kg | Talla: {h['triaje_talla']} m | IMC: {h['imc']}", ln=True)
            pdf.set_font("Arial", 'B', 10); pdf.cell(30, 6, txt="Diagnostico:"); pdf.set_font("Arial", '', 10); pdf.multi_cell(160, 6, txt=f"{h['diagnostico']}")
            if h['medicina']:
                pdf.set_font("Arial", 'B', 10); pdf.cell(30, 6, txt="Tratamiento:"); pdf.set_font("Arial", '', 10); pdf.multi_cell(160, 6, txt=f"{h['medicina']} - {h['frecuencia']} (Cant: {h['cantidad']})")
            pdf.ln(4)
            
    nombre_archivo = f"historia_clinica_{paciente_id}.pdf"
    pdf.output(nombre_archivo)
    return send_file(nombre_archivo, as_attachment=True)

@app.route('/descargar_receta/<int:consulta_id>')
@login_requerido
def descargar_receta(consulta_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    query = """
        SELECT cons.diagnostico, cons.medicina, cons.frecuencia, cons.cantidad, cons.tipo_atencion,
               c.fecha, p.nombre as paciente_nombre, p.dni as paciente_dni,
               m.nombre as medico_nombre, m.cmp as medico_cmp, e.nombre as especialidad
        FROM consultas cons 
        JOIN citas c ON cons.cita_id = c.id 
        JOIN pacientes p ON c.paciente_id = p.id
        LEFT JOIN medicos m ON c.medico_id = m.id
        LEFT JOIN especialidades e ON m.especialidad_id = e.id
        WHERE cons.id = ?
    """
    cursor.execute(query, (consulta_id,))
    receta = cursor.fetchone()
    conexion.close()
    if not receta: return "Consulta no encontrada", 404
    
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image('526422900_774722791753650_413711329622849230_n.jpg', x=15, y=10, w=35)
    except: pass
    pdf.set_y(15)
    pdf.set_font("Arial", 'B', 24); pdf.cell(200, 10, txt="GASTROCLINIC", ln=True, align='C')
    tipo_doc_label = "REPORTE DE CONTROL" if receta['tipo_atencion'] == 'Control' else "RECETA MEDICA / CONSULTA"
    pdf.set_font("Arial", 'B', 13); pdf.cell(200, 8, txt=tipo_doc_label, ln=True, align='C')
    pdf.line(10, 40, 200, 40); pdf.ln(15)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(35, 8, txt="Paciente:"); pdf.set_font("Arial", '', 11); pdf.cell(90, 8, txt=f"{receta['paciente_nombre']}")
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(15, 8, txt="DNI:"); pdf.set_font("Arial", '', 11); pdf.cell(40, 8, txt=f"{receta['paciente_dni']}", ln=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(35, 8, txt="Fecha Atencion:"); pdf.set_font("Arial", '', 11); pdf.cell(90, 8, txt=f"{receta['fecha']}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(40, 8, txt="Diagnostico / Notas:"); pdf.set_font("Arial", '', 11); pdf.multi_cell(150, 7, txt=f"{receta['diagnostico']}")
    pdf.ln(5)
    
    if receta['medicina']:
        pdf.set_font("Arial", 'B', 14); pdf.cell(200, 10, txt="Prescripcion Medica", ln=True)
        pdf.set_font("Arial", 'B', 11); pdf.cell(35, 7, txt="Medicamento:"); pdf.set_font("Arial", '', 11); pdf.cell(150, 7, txt=f"{receta['medicina']}", ln=True)
        pdf.set_font("Arial", 'B', 11); pdf.cell(35, 7, txt="Cantidad:"); pdf.set_font("Arial", '', 11); pdf.cell(150, 7, txt=f"{receta['cantidad']}", ln=True)
        pdf.set_font("Arial", 'B', 11); pdf.cell(35, 7, txt="Indicaciones:"); pdf.set_font("Arial", '', 11); pdf.multi_cell(150, 7, txt=f"{receta['frecuencia']}")
    
    pdf.set_y(-60)
    pdf.set_font("Arial", '', 11); pdf.cell(200, 8, txt="____________________________________________", ln=True, align='C')
    pdf.set_font("Arial", 'B', 11); pdf.cell(200, 6, txt=f"Dr/a. {receta['medico_nombre'] or 'Sin registrar'}", ln=True, align='C')
    pdf.set_font("Arial", '', 11); pdf.cell(200, 6, txt=f"Especialidad: {receta['especialidad'] or 'General'}", ln=True, align='C')
    pdf.cell(200, 6, txt=f"CMP: {receta['medico_cmp'] or '-'}", ln=True, align='C')
    
    nombre = f"receta_{consulta_id}.pdf"; pdf.output(nombre)
    return send_file(nombre, as_attachment=True)

@app.route('/agregar_usuario', methods=['POST'])
@login_requerido
def agregar_usuario():
    if session.get('rol') != 'administrador': return redirect('/')
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("INSERT INTO usuarios (username, password, rol, nombres, dni) VALUES (?, ?, ?, ?, ?)", 
                       (request.form['username'], request.form['password'], request.form['rol'], request.form['nombres'], request.form['dni']))
        conexion.commit(); flash("✅ Usuario creado exitosamente.")
    except sqlite3.IntegrityError: flash("❌ Error: Ese nombre de usuario ya existe.")
    finally: conexion.close()
    return redirect('/')

@app.route('/eliminar_usuario/<int:id_usuario>')
@login_requerido
def eliminar_usuario(id_usuario):
    if session.get('rol') != 'administrador': return redirect('/')
    if id_usuario == session['usuario_id']: flash("❌ No puedes eliminarte a ti mismo."); return redirect('/')
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_usuario,))
    conexion.commit(); conexion.close(); flash("✅ Usuario eliminado.")
    return redirect('/')

@app.route('/agregar_especialidad', methods=['POST'])
@login_requerido
def agregar_especialidad():
    if session.get('rol') != 'administrador': return redirect('/')
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try: cursor.execute("INSERT INTO especialidades (nombre) VALUES (?)", (request.form['nombre'],)); conexion.commit(); flash("✅ Especialidad agregada.")
    except sqlite3.IntegrityError: flash("❌ Error: Especialidad ya existe.")
    finally: conexion.close()
    return redirect('/')

@app.route('/eliminar_especialidad/<int:id_esp>')
@login_requerido
def eliminar_especialidad(id_esp):
    if session.get('rol') != 'administrador': return redirect('/')
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try: cursor.execute("DELETE FROM especialidades WHERE id = ?", (id_esp,)); conexion.commit(); flash("✅ Especialidad eliminada.")
    except: flash("❌ Error: Elimina primero los médicos de esta especialidad.")
    finally: conexion.close()
    return redirect('/')

@app.route('/agregar_medico', methods=['POST'])
@login_requerido
def agregar_medico():
    if session.get('rol') != 'administrador': return redirect('/')
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try: cursor.execute("INSERT INTO medicos (nombre, dni, cmp, especialidad_id) VALUES (?, ?, ?, ?)", (request.form['nombre'], request.form['dni'], request.form['cmp'], request.form['especialidad_id'])); conexion.commit(); flash("✅ Médico agregado.")
    except sqlite3.IntegrityError: flash("❌ Error: DNI duplicado.")
    finally: conexion.close()
    return redirect('/')

@app.route('/eliminar_medico/<int:id_med>')
@login_requerido
def eliminar_medico(id_med):
    if session.get('rol') != 'administrador': return redirect('/')
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM medicos WHERE id = ?", (id_med,)); conexion.commit(); conexion.close(); flash("✅ Médico eliminado.")
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, port=5000)