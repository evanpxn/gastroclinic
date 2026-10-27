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
        alergias TEXT, grupo_sanguineo TEXT
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
        FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
        FOREIGN KEY (medico_id) REFERENCES medicos(id)
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS consultas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cita_id INTEGER, diagnostico TEXT, medicina TEXT,
        frecuencia TEXT, cantidad TEXT, tratamiento TEXT,
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
    
    # Migración automática segura
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

# --- PLANTILLA HTML: LOGIN TECH ---
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Login Tech - Gastro Clinic</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .login-card {
            background: rgba(30, 41, 59, 0.85);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 24px;
            box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.7);
            width: 400px;
            padding: 2.5rem;
            color: #fff;
        }
        .form-control {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #fff;
            border-radius: 12px;
            padding: 12px 16px;
        }
        .form-control:focus {
            background: rgba(15, 23, 42, 0.9);
            border-color: #38bdf8;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
            color: #fff;
        }
        .btn-tech {
            background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%);
            border: none;
            color: #fff;
            font-weight: 700;
            padding: 12px;
            border-radius: 12px;
            box-shadow: 0 10px 20px -5px rgba(37, 99, 235, 0.5);
            transition: all 0.3s ease;
        }
        .btn-tech:hover { transform: translateY(-2px); color: #fff; }
    </style>
</head>
<body>
    <div class="login-card text-center">
        <div class="mb-4">
            <img src="/logo_clinica" alt="Gastro Clinic" class="img-fluid rounded-4 shadow" style="max-height: 90px; background: #fff; padding: 6px;">
            <h4 class="fw-bold mt-3 mb-1 text-white">Gastro Clinic</h4>
            <p class="text-info small font-monospace">FANDA SYSTEM - MÉDICO</p>
        </div>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for msg in messages %}<div class="alert alert-danger py-2 border-0 rounded-3 small">{{ msg }}</div>{% endfor %}
            {% endif %}
        {% endwith %}
        <form action="/login" method="POST" class="text-start">
            <div class="mb-3">
                <label class="form-label small fw-semibold text-light">Usuario</label>
                <input type="text" name="username" class="form-control" placeholder="Ingrese usuario" required autofocus>
            </div>
            <div class="mb-4">
                <label class="form-label small fw-semibold text-light">Contraseña</label>
                <input type="password" name="password" class="form-control" placeholder="••••••••" required>
            </div>
            <button type="submit" class="btn btn-tech w-100 fs-6">Acceder al Panel ➔</button>
        </form>
    </div>
</body>
</html>
"""

# --- PLANTILLA HTML: DASHBOARD TECH ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gastro Clinic - Dashboard Tech</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <!-- Chart.js para gráficas avanzadas -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --brand-primary: #0284c7;
            --brand-accent: #38bdf8;
            --card-radius: 20px;
        }
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: linear-gradient(rgba(248, 250, 252, 0.92), rgba(241, 245, 249, 0.94)), 
                        url('https://images.unsplash.com/photo-1551076805-e1869033e561?auto=format&fit=crop&w=1920&q=80');
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
            color: #334155;
            overflow-x: hidden;
        }
        .navbar-tech {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            box-shadow: 0 10px 30px -5px rgba(0,0,0,0.25);
            padding: 12px 24px;
            border-bottom: 2px solid rgba(56, 189, 248, 0.3);
        }
        .ekg-container { width: 140px; height: 35px; display: inline-block; position: relative; overflow: hidden; }
        .ekg-line { stroke: #38bdf8; stroke-width: 2.5; fill: none; stroke-dasharray: 300; stroke-dashoffset: 300; animation: ekgAnim 2.5s linear infinite; }
        @keyframes ekgAnim { 0% { stroke-dashoffset: 300; } 50% { stroke-dashoffset: 0; } 100% { stroke-dashoffset: -300; } }
        .live-dot { width: 10px; height: 10px; background-color: #22c55e; border-radius: 50%; display: inline-block; animation: pulseDot 2s infinite; }
        @keyframes pulseDot { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); } 70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); } }
        .nav-tabs-tech { border-bottom: none; gap: 10px; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(10px); padding: 10px; border-radius: 18px; box-shadow: 0 10px 25px rgba(0,0,0,0.06); margin-bottom: 24px; }
        .nav-tabs-tech .nav-link { border: none !important; border-radius: 12px !important; color: #475569; font-weight: 600; padding: 10px 18px; transition: all 0.3s ease; }
        .nav-tabs-tech .nav-link:hover { color: var(--brand-primary); background: #f1f5f9; transform: translateY(-2px); }
        .nav-tabs-tech .nav-link.active { background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important; color: #ffffff !important; box-shadow: 0 8px 20px -4px rgba(2, 132, 199, 0.4); transform: translateY(-2px); }
        .card-tech { background: rgba(255, 255, 255, 0.92); backdrop-filter: blur(12px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: var(--card-radius); box-shadow: 0 15px 35px -5px rgba(0,0,0,0.05); transition: all 0.3s ease; }
        .card-header-tech { border-bottom: 1px solid rgba(241, 245, 249, 0.8); background: transparent; padding: 20px 24px; }
        .form-control, .form-select { border-radius: 12px; border: 1.5px solid #cbd5e1; background: rgba(255, 255, 255, 0.9); padding: 11px 16px; font-size: 0.93rem; }
        .form-control:focus, .form-select:focus { border-color: var(--brand-primary); background: #ffffff; box-shadow: 0 0 0 4px rgba(2, 132, 199, 0.15); }
        .btn-action-primary { background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%); border: none; color: #fff; font-weight: 700; border-radius: 12px; padding: 12px 20px; box-shadow: 0 8px 20px -4px rgba(2, 132, 199, 0.4); transition: all 0.3s ease; }
        .btn-action-primary:hover { transform: translateY(-3px); color: #fff; }
        .table-tech th { background: rgba(241, 245, 249, 0.8); color: #334155; font-size: 0.82rem; text-transform: uppercase; padding: 14px 16px; }
        .table-tech td { padding: 14px 16px; vertical-align: middle; border-color: #f1f5f9; }
        .badge-soft-primary { background: #e0f2fe; color: #0369a1; font-weight: 600; border-radius: 8px; padding: 6px 10px; }
        .badge-soft-danger { background: #ffe4e6; color: #9f1239; font-weight: 600; border-radius: 8px; padding: 6px 10px; }
        .badge-soft-success { background: #dcfce7; color: #166534; font-weight: 600; border-radius: 8px; padding: 6px 10px; }
    </style>
</head>
<body>

    <nav class="navbar navbar-dark navbar-tech mb-4">
        <div class="container-fluid px-4 d-flex justify-content-between align-items-center">
            <div class="d-flex align-items-center gap-3">
                <img src="/logo_clinica" alt="Logo" height="42" class="rounded-3 bg-white p-1 shadow">
                <div>
                    <span class="fw-bold text-white fs-5 tracking-tight">Gastro Clinic</span>
                    <div class="d-flex align-items-center gap-2">
                        <span class="live-dot"></span>
                        <small class="text-info font-monospace" style="font-size: 0.72rem;">SISTEMA ACTIVO</small>
                    </div>
                </div>
                <div class="ekg-container d-none d-md-block ms-3">
                    <svg viewBox="0 0 150 40" width="140" height="35">
                        <path class="ekg-line" d="M0,20 L30,20 L38,5 L45,35 L55,10 L63,25 L70,20 L150,20" />
                    </svg>
                </div>
            </div>
            
            <div class="d-flex align-items-center gap-3">
                <span class="text-light small">👤 <strong class="text-info">{{ session['username']|capitalize }}</strong> <span class="badge bg-secondary ms-1">{{ session['rol']|capitalize }}</span></span>
                <a href="/logout" class="btn btn-outline-light btn-sm fw-bold rounded-3 px-3 shadow-sm">Salir 🚪</a>
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

        <!-- PESTAÑAS -->
        <ul class="nav nav-tabs-tech" id="clinicaTabs" role="tablist">
            <li class="nav-item"><button class="nav-link active" id="pacientes-tab" data-bs-toggle="tab" data-bs-target="#pacientes" type="button">👤 Pacientes & Fichas</button></li>
            <li class="nav-item"><button class="nav-link" id="citas-tab" data-bs-toggle="tab" data-bs-target="#citas" type="button">📅 Agenda Citas</button></li>
            
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
                            <h6 class="fw-bold text-secondary mb-3">1. Datos Personales</h6>
                            <div class="row g-3 mb-4">
                                <div class="col-md-3"><label class="form-label small fw-semibold">Nombre Completo</label><input type="text" name="nombre" class="form-control" required placeholder="Ej. Ana Torres"></div>
                                <div class="col-md-2"><label class="form-label small fw-semibold">DNI</label><input type="text" name="dni" class="form-control" required placeholder="8 dígitos"></div>
                                <div class="col-md-2"><label class="form-label small fw-semibold">F. Nacimiento</label><input type="date" name="fecha_nacimiento" class="form-control" required></div>
                                <div class="col-md-2"><label class="form-label small fw-semibold">Sexo</label><select name="sexo" class="form-select" required><option value="Masculino">Masculino</option><option value="Femenino">Femenino</option><option value="Otro">Otro</option></select></div>
                                <div class="col-md-3"><label class="form-label small fw-semibold">Celular</label><input type="text" name="celular" class="form-control" placeholder="987654321"></div>
                                <div class="col-md-12"><label class="form-label small fw-semibold">Dirección</label><input type="text" name="direccion" class="form-control" placeholder="Jr. Los Pinos #456"></div>
                            </div>

                            <h6 class="fw-bold text-secondary mb-3">2. Perfil Clínico</h6>
                            <div class="row g-3 mb-4">
                                <div class="col-md-2">
                                    <label class="form-label small fw-semibold text-danger">Grupo Sanguíneo</label>
                                    <select name="grupo_sanguineo" class="form-select border-danger">
                                        <option value="O+">O+</option><option value="O-">O-</option><option value="A+">A+</option><option value="A-">A-</option>
                                        <option value="B+">B+</option><option value="B-">B-</option><option value="AB+">AB+</option><option value="AB-">AB-</option>
                                    </select>
                                </div>
                                <div class="col-md-5"><label class="form-label small fw-semibold text-danger">Alergias</label><textarea name="alergias" class="form-control border-danger" rows="1" placeholder="Ej. Ninguna"></textarea></div>
                                <div class="col-md-5"><label class="form-label small fw-semibold">Motivo de Consulta</label><textarea name="motivo_consulta" class="form-control" rows="1" placeholder="Síntomas..."></textarea></div>
                                <div class="col-md-6"><label class="form-label small fw-semibold">Antecedentes</label><textarea name="antecedentes" class="form-control" rows="2" placeholder="Enfermedades pasadas..."></textarea></div>
                                <div class="col-md-6"><label class="form-label small fw-semibold">Diagnósticos Previos</label><textarea name="diagnosticos" class="form-control" rows="2" placeholder="Historial clínico..."></textarea></div>
                            </div>
                            <button type="submit" class="btn btn-action-primary w-100 fs-6">💾 Guardar Ficha Médica</button>
                        </form>
                    </div>
                </div>

                <div class="card-tech">
                    <div class="card-header-tech"><h5 class="fw-bold m-0 text-dark">📋 Directorio de Pacientes</h5></div>
                    <div class="table-responsive">
                        <table class="table table-tech align-middle">
                            <thead><tr><th>ID</th><th>Paciente</th><th>DNI</th><th>Nacimiento</th><th>Celular</th><th>Sangre</th><th>Alergias</th><th>Historial PDF</th></tr></thead>
                            <tbody>
                                {% for p in pacientes %}
                                <tr>
                                    <td class="fw-bold text-muted">#{{ p.id }}</td>
                                    <td><div class="fw-bold text-dark">{{ p.nombre }}</div><small class="text-muted">{{ p.sexo }}</small></td>
                                    <td><span class="badge bg-light text-dark border">{{ p.dni }}</span></td>
                                    <td>{{ p.fecha_nacimiento }}</td><td>{{ p.celular }}</td>
                                    <td><span class="badge badge-soft-danger">{{ p.grupo_sanguineo }}</span></td>
                                    <td><small class="text-danger fw-semibold">{{ p.alergias or 'Ninguna' }}</small></td>
                                    <td><a href="/descargar_historia_paciente/{{ p.id }}" target="_blank" class="btn btn-outline-primary btn-sm fw-bold rounded-3">📄 Ver Historia</a></td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- PESTAÑA: CITAS -->
            <div class="tab-pane fade" id="citas">
                <div class="row g-4">
                    <div class="col-md-4">
                        <div class="card-tech p-4">
                            <h5 class="fw-bold text-success mb-3">📅 Agendar Cita</h5>
                            <form action="/agendar_cita" method="POST">
                                <div class="mb-3">
                                    <label class="form-label small fw-semibold">🔍 Buscar Paciente (Nombre o DNI)</label>
                                    <input type="text" id="buscadorPacienteCita" class="form-control mb-2" placeholder="Escriba para filtrar..." onkeyup="filtrarSelectPacientes()">
                                    <label class="form-label small fw-semibold">Seleccionar Paciente Filtrado</label>
                                    <select name="paciente_id" id="selectPacienteCita" class="form-select" required size="4" style="height: 120px;">
                                        {% for p in pacientes %}<option value="{{ p.id }}">{{ p.nombre }} - DNI: {{ p.dni }}</option>{% endfor %}
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label small fw-semibold">Médico</label>
                                    <select name="medico_id" class="form-select" required>
                                        <option value="">-- Seleccionar Médico --</option>
                                        {% for m in medicos %}<option value="{{ m.id }}">Dr/a. {{ m.nombre }} ({{ m.especialidad }})</option>{% endfor %}
                                    </select>
                                </div>
                                <div class="mb-4">
                                    <label class="form-label small fw-semibold">Fecha y Hora</label>
                                    <input type="datetime-local" name="fecha" class="form-control" required>
                                </div>
                                <button type="submit" class="btn btn-success w-100 fw-bold rounded-3 py-2">✅ Confirmar Cita</button>
                            </form>
                        </div>
                    </div>
                    <div class="col-md-8">
                        <div class="card-tech">
                            <div class="card-header-tech"><h5 class="fw-bold m-0">🗓️ Citas Pendientes</h5></div>
                            <div class="table-responsive">
                                <table class="table table-tech align-middle">
                                    <thead><tr><th>Fecha / Hora</th><th>Médico</th><th>Paciente</th><th>Ficha Resumida</th></tr></thead>
                                    <tbody>
                                        {% for c in citas %}
                                        <tr>
                                            <td class="fw-bold text-primary">{{ c.fecha }}</td>
                                            <td><div class="fw-semibold">Dr/a. {{ c.medico_nombre or 'General' }}</div><small class="text-muted">{{ c.especialidad or 'General' }}</small></td>
                                            <td class="fw-bold">{{ c.paciente_nombre }}</td>
                                            <td>
                                                <div class="p-2 bg-light rounded-3 small">
                                                    <span class="text-danger fw-semibold">Sangre:</span> {{ c.grupo_sanguineo }} | 
                                                    <span class="text-danger fw-semibold">Alergias:</span> {{ c.alergias or 'Ninguna' }}
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

            {% if session['rol'] in ['administrador', 'medico'] %}
            <!-- PESTAÑA: CONSULTAS -->
            <div class="tab-pane fade" id="consultas">
                <div class="row g-4">
                    <div class="col-md-4">
                        <div class="card-tech p-4 border-danger">
                            <h5 class="fw-bold text-danger mb-3">🩺 Registrar Atención</h5>
                            <form action="/registrar_consulta" method="POST">
                                <div class="mb-3">
                                    <label class="form-label small fw-semibold">Paciente en Espera</label>
                                    <select name="cita_id" class="form-select border-danger" required>
                                        <option value="">-- Seleccionar Cita --</option>
                                        {% for c in citas %}<option value="{{ c.id }}">{{ c.paciente_nombre }} - DNI: {{ c.paciente_dni }}</option>{% endfor %}
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label small fw-semibold">Diagnóstico</label>
                                    <textarea name="diagnostico" class="form-control" rows="3" required placeholder="Escriba el diagnóstico..."></textarea>
                                </div>
                                <hr class="my-3">
                                <h6 class="fw-bold text-primary mb-2">Prescripción</h6>
                                <div class="mb-2"><input type="text" name="medicina" class="form-control" required placeholder="Medicina (ej. Amoxicilina)"></div>
                                <div class="mb-2"><input type="text" name="frecuencia" class="form-control" required placeholder="Indicaciones (ej. Cada 8h)"></div>
                                <div class="mb-4"><input type="text" name="cantidad" class="form-control" required placeholder="Cantidad (ej. 15 tabletas)"></div>
                                <button type="submit" class="btn btn-danger w-100 fw-bold rounded-3 py-2">💾 Guardar & Receta PDF</button>
                            </form>
                        </div>
                    </div>
                    <div class="col-md-8">
                        <div class="card-tech">
                            <div class="card-header-tech d-flex justify-content-between align-items-center">
                                <h5 class="fw-bold m-0">📚 Historial de Consultas</h5>
                                <input type="text" id="buscadorHistorial" class="form-control form-control-sm w-50" placeholder="🔍 Buscar..." onkeyup="filtrarHistorial()">
                            </div>
                            <div class="table-responsive" style="max-height: 500px; overflow-y: auto;">
                                <table class="table table-tech align-middle" id="tablaHistorial">
                                    <thead><tr><th>Fecha</th><th>Paciente</th><th>Diagnóstico</th><th>Médico</th><th>Acción</th></tr></thead>
                                    <tbody>
                                        {% for cons in consultas %}
                                        <tr class="fila-historial">
                                            <td class="small">{{ cons.fecha }}</td>
                                            <td class="nombre-dni"><div class="fw-bold">{{ cons.paciente_nombre }}</div><small class="text-muted">DNI: {{ cons.paciente_dni }}</small></td>
                                            <td><div style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ cons.diagnostico }}</div></td>
                                            <td>Dr/a. {{ cons.medico_nombre }}</td>
                                            <td><a href="/descargar_receta/{{ cons.id }}" target="_blank" class="btn btn-outline-danger btn-sm fw-bold rounded-3">📄 PDF</a></td>
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
                    <!-- Columna Izquierda: Registro de Medicamento y Facturación Dual -->
                    <div class="col-md-4">
                        <!-- Registrar Medicamento -->
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

                        <!-- Facturación y Caja -->
                        <div class="card-tech p-4 border-warning">
                            <h5 class="fw-bold text-dark mb-3">🧾 Caja y Facturación</h5>
                            <form action="/facturar_transaccion" method="POST">
                                <div class="mb-2">
                                    <label class="form-label small fw-semibold">Tipo de Transacción</label>
                                    <select name="tipo_transaccion" id="tipoTransaccion" class="form-select fw-bold text-primary" onchange="cambiarTipoTransaccion()" required>
                                        <option value="Medicamento">Venta de Medicamentos</option>
                                        <option value="Consulta">Cobro de Consulta Médica</option>
                                    </select>
                                </div>
                                <div class="mb-2"><input type="text" name="documento_cliente" class="form-control" required placeholder="DNI / RUC del Cliente"></div>
                                <div class="mb-3"><input type="text" name="cliente_nombre" class="form-control" required placeholder="Nombre / Razón Social"></div>
                                
                                <!-- Campos para Medicamentos -->
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

                                <!-- Campos para Cobro de Consulta Médica -->
                                <div id="seccionConsulta" style="display: none;">
                                    <div class="mb-3">
                                        <label class="form-label small fw-semibold text-danger">🩺 Seleccionar Atención Realizada</label>
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
                                        <label class="form-label small fw-semibold">👨‍⚕️ Médico Atendedor (Automático)</label>
                                        <input type="text" id="medicoNombreDisplay" class="form-control bg-light fw-bold text-secondary" readonly placeholder="Se autocompletará...">
                                        <input type="hidden" name="medico_id" id="medicoIdInput">
                                    </div>

                                    <div class="row g-2 mb-3">
                                        <div class="col-md-6">
                                            <label class="form-label small fw-semibold text-primary">🏥 Monto Clínica (S/)</label>
                                            <input type="number" step="0.01" name="monto_clinica" id="montoClinica" class="form-control" placeholder="0.00" min="0" oninput="calcularTotalConsulta()">
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label small fw-semibold text-success">👨‍⚕️ Monto Médico (S/)</label>
                                            <input type="number" step="0.01" name="monto_medico" id="montoMedico" class="form-control" placeholder="0.00" min="0" oninput="calcularTotalConsulta()">
                                        </div>
                                    </div>

                                    <div class="mb-3">
                                        <label class="form-label small fw-bold text-dark">💰 Monto Total Consulta (S/)</label>
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
                            let medicoId = option.getAttribute("data-medico-id");
                            let medicoNombre = option.getAttribute("data-medico-nombre");

                            document.getElementById("medicoIdInput").value = medicoId || "";
                            document.getElementById("medicoNombreDisplay").value = medicoNombre ? "Dr/a. " + medicoNombre : "";
                        }

                        function calcularTotalConsulta() {
                            let clinica = parseFloat(document.getElementById("montoClinica").value) || 0;
                            let medico = parseFloat(document.getElementById("montoMedico").value) || 0;
                            let total = clinica + medico;
                            document.getElementById("montoTotalConsulta").value = total.toFixed(2);
                        }
                    </script>

                    <!-- Columna Derecha: Inventario y Registro de Ventas -->
                    <div class="col-md-8">
                        <div class="card-tech mb-4">
                            <div class="card-header-tech"><h5 class="fw-bold m-0">💊 Inventario Actual de Medicamentos</h5></div>
                            <div class="table-responsive" style="max-height: 250px; overflow-y: auto;">
                                <table class="table table-tech align-middle">
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
                                <table class="table table-tech align-middle">
                                    <thead><tr><th>Tipo / Comp.</th><th>Cliente</th><th>Detalle / Médico</th><th>Total / División</th><th>Recibo</th></tr></thead>
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
                                            <td><a href="/descargar_recibo/{{ v.id }}" target="_blank" class="btn btn-sm btn-light border fw-bold">📄 PDF</a></td>
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
            <!-- PESTAÑA: REPORTES Y FINANZAS CON CALENDARIO Y GRÁFICAS HORIZONTALES -->
            <div class="tab-pane fade" id="reportes">
                <div class="row g-4">
                    <!-- Controles de Calendario / Filtro por Tipo y Fecha -->
                    <div class="col-md-12">
                        <div class="card-tech p-4">
                            <div class="row align-items-center g-3">
                                <div class="col-md-4">
                                    <h5 class="fw-bold text-success m-0">📊 Panel Financiero & Gráficas</h5>
                                    <small class="text-muted">Filtre ingresos por calendario interactivo</small>
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label small fw-semibold">Tipo de Vista</label>
                                    <select id="filtroModo" class="form-select fw-bold text-primary" onchange="cambiarModoFiltro()">
                                        <option value="dia">📅 Por Día (Calendario Diario)</option>
                                        <option value="mes">🗓️ Por Mes (Calendario Mensual)</option>
                                        <option value="ano">📈 Por Año (Selector Anual)</option>
                                    </select>
                                </div>
                                <div class="col-md-3">
                                    <label class="form-label small fw-semibold" id="labelSelectorFecha">Seleccionar Fecha / Periodo</label>
                                    <!-- Selector dinámico según modo -->
                                    <input type="date" id="inputDia" class="form-control selector-fecha" onchange="filtrarGrafica()">
                                    <input type="month" id="inputMes" class="form-control selector-fecha" style="display:none;" onchange="filtrarGrafica()">
                                    <select id="inputAno" class="form-select selector-fecha" style="display:none;" onchange="filtrarGrafica()">
                                        {% for r in rep_anos %}
                                        <option value="{{ r.periodo }}">{{ r.periodo }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                                <div class="col-md-2 text-end">
                                    <button class="btn btn-outline-secondary btn-sm fw-bold mt-4" onclick="resetFiltros()">🔄 Ver Todo</button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Gráfica de Barras Horizontales con Chart.js -->
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

                    <!-- Tablas Resumen Detalladas -->
                    <div class="col-md-12">
                        <div class="card-tech p-4">
                            <h6 class="fw-bold text-secondary mb-3">📋 Resumen Detallado de Ingresos</h6>
                            <div class="table-responsive">
                                <table class="table table-tech align-middle" id="tablaReportesDetalle">
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

            <!-- Script para inicializar y actualizar la gráfica horizontal de barras -->
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
                    
                    // Mostrar filas correspondientes en la tabla
                    let filas = document.querySelectorAll("#tbodyReportes tr");
                    filas.forEach(f => {
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
                                {
                                    label: '🏥 Clínica (S/)',
                                    data: clinicaData,
                                    backgroundColor: '#0284c7',
                                    borderRadius: 8
                                },
                                {
                                    label: '👨‍⚕️ Médicos (S/)',
                                    data: medicosData,
                                    backgroundColor: '#22c55e',
                                    borderRadius: 8
                                }
                            ]
                        },
                        options: {
                            indexAxis: 'y', // Configuración clave para barras horizontales en Chart.js v3+
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                x: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                                y: { grid: { display: false } }
                            }
                        }
                    });
                }

                function filtrarGrafica() {
                    let modo = document.getElementById("filtroModo").value;
                    let valorFiltro = "";
                    if(modo === 'dia') valorFiltro = document.getElementById("inputDia").value;
                    else if(modo === 'mes') valorFiltro = document.getElementById("inputMes").value;
                    else if(modo === 'ano') valorFiltro = document.getElementById("inputAno").value;

                    let filas = document.querySelectorAll("#tbodyReportes tr");
                    let clinicaVals = [];
                    let medicosVals = [];
                    let labelPeriodos = [];

                    filas.forEach(f => {
                        if(f.getAttribute("data-tipo") === modo) {
                            let periodo = f.getAttribute("data-periodo");
                            if(!valorFiltro || periodo === valorFiltro) {
                                labelPeriodos.push(periodo);
                                clinicaVals.push(parseFloat(f.getAttribute("data-clinica")));
                                medicosVals.push(parseFloat(f.getAttribute("data-medicos")));
                            }
                        }
                    });

                    if(labelPeriodos.length === 0) {
                        labelPeriodos = [valorFiltro || 'Seleccione Fecha'];
                        clinicaVals = [0];
                        medicosVals = [0];
                    }

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
                                <button type="submit" class="btn btn-primary w-100 fw-bold">👨‍⚕️ Registrar Médico</button>
                            </form>
                        </div>
                        <div class="card-tech p-4">
                            <h5 class="fw-bold text-secondary mb-3">👨‍⚕️ Staff Médico</h5>
                            <div class="table-responsive">
                                <table class="table table-tech align-middle">
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
                                <table class="table table-tech align-middle">
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
        SELECT c.id, c.fecha, c.estado, 
               p.nombre as paciente_nombre, p.dni as paciente_dni, p.motivo_consulta, p.antecedentes, p.diagnosticos, p.alergias, p.grupo_sanguineo,
               m.nombre as medico_nombre, e.nombre as especialidad
        FROM citas c 
        JOIN pacientes p ON c.paciente_id = p.id 
        LEFT JOIN medicos m ON c.medico_id = m.id
        LEFT JOIN especialidades e ON m.especialidad_id = e.id
        WHERE c.estado = 'pendiente' ORDER BY c.fecha ASC
    """
    cursor.execute(query_citas)
    citas = cursor.fetchall()
    
    query_consultas = """
        SELECT cons.id, cons.diagnostico, cons.medicina, cons.frecuencia, cons.cantidad,
               c.fecha, p.nombre as paciente_nombre, p.dni as paciente_dni,
               m.id as medico_id, m.nombre as medico_nombre
        FROM consultas cons 
        JOIN citas c ON cons.cita_id = c.id 
        JOIN pacientes p ON c.paciente_id = p.id
        LEFT JOIN medicos m ON c.medico_id = m.id
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
    
    # Consultas para Reportes y Finanzas (Días, Meses, Años)
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
    if session.get('rol') == 'administrador':
        cursor.execute("SELECT * FROM usuarios ORDER BY id ASC")
        usuarios = cursor.fetchall()
        cursor.execute("SELECT * FROM especialidades ORDER BY nombre ASC")
        especialidades = cursor.fetchall()
        
    conexion.close()
    return render_template_string(HTML_TEMPLATE, pacientes=pacientes, citas=citas, consultas=consultas, medicamentos=medicamentos, ventas=ventas, usuarios=usuarios, especialidades=especialidades, medicos=medicos, rep_dias=rep_dias, rep_meses=rep_meses, rep_anos=rep_anos)

@app.route('/agregar_paciente', methods=['POST'])
@login_requerido
def agregar_paciente():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    query = "INSERT INTO pacientes (nombre, dni, sexo, fecha_nacimiento, direccion, celular, motivo_consulta, antecedentes, diagnosticos, alergias, grupo_sanguineo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    valores = (request.form['nombre'], request.form['dni'], request.form.get('sexo', ''), request.form.get('fecha_nacimiento', ''), request.form.get('direccion', ''), request.form.get('celular', ''), request.form.get('motivo_consulta', ''), request.form.get('antecedentes', ''), request.form.get('diagnosticos', ''), request.form.get('alergias', ''), request.form.get('grupo_sanguineo', ''))
    try:
        cursor.execute(query, valores)
        conexion.commit(); flash("✅ Ficha Médica creada exitosamente.")
    except sqlite3.IntegrityError: flash(f"❌ Error: El DNI ya está registrado.")
    finally: conexion.close()
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
    pdf.set_font("Arial", 'B', 20); pdf.cell(200, 10, txt="GASTRO CLINIC", ln=True, align='C')
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
    
    if venta['tipo_transaccion'] == 'Consulta':
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 10); pdf.cell(200, 8, txt="Distribucion de Ingresos de Consulta:", ln=True)
        pdf.set_font("Arial", size=10); pdf.cell(200, 6, txt=f"- Ingreso para la Clinica: S/ {venta['monto_clinica']:.2f}", ln=True)
        pdf.cell(200, 6, txt=f"- Ingreso para el Medico {venta['medico_nombre']}: S/ {venta['monto_medico']:.2f}", ln=True)
        
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
        SELECT cons.id, cons.diagnostico, cons.medicina, cons.frecuencia, cons.cantidad,
               c.fecha, m.nombre as medico_nombre, e.nombre as especialidad
        FROM consultas cons
        JOIN citas c ON cons.cita_id = c.id
        LEFT JOIN medicos m ON c.medico_id = m.id
        LEFT JOIN especialidades e ON m.especialidad_id = e.id
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
    pdf.set_font("Arial", 'B', 22); pdf.cell(200, 10, txt="GASTRO CLINIC", ln=True, align='C')
    pdf.set_font("Arial", 'B', 13); pdf.cell(200, 8, txt="HISTORIA CLINICA GENERAL DEL PACIENTE", ln=True, align='C')
    pdf.line(10, 38, 200, 38); pdf.ln(12)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(200, 8, txt="1. DATOS PERSONALES", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Nombre:"); pdf.set_font("Arial", '', 10); pdf.cell(100, 6, txt=f"{paciente['nombre']}", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="DNI:"); pdf.set_font("Arial", '', 10); pdf.cell(60, 6, txt=f"{paciente['dni']}")
    pdf.set_font("Arial", 'B', 10); pdf.cell(25, 6, txt="Sexo:"); pdf.set_font("Arial", '', 10); pdf.cell(50, 6, txt=f"{paciente['sexo']}", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="F. Nacimiento:"); pdf.set_font("Arial", '', 10); pdf.cell(60, 6, txt=f"{paciente['fecha_nacimiento']}")
    pdf.set_font("Arial", 'B', 10); pdf.cell(25, 6, txt="Celular:"); pdf.set_font("Arial", '', 10); pdf.cell(50, 6, txt=f"{paciente['celular'] or 'No registrado'}", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Direccion:"); pdf.set_font("Arial", '', 10); pdf.cell(150, 6, txt=f"{paciente['direccion'] or 'No registrada'}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(200, 8, txt="2. PERFIL CLINICO E HISTORIAL INICIAL", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Grupo Sanguineo:"); pdf.set_font("Arial", '', 10); pdf.cell(150, 6, txt=f"{paciente['grupo_sanguineo'] or 'No especificado'}", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Alergias:"); pdf.set_font("Arial", '', 10); pdf.cell(150, 6, txt=f"{paciente['alergias'] or 'Ninguna'}", ln=True)
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Motivo Consulta:"); pdf.set_font("Arial", '', 10); pdf.multi_cell(150, 6, txt=f"{paciente['motivo_consulta'] or 'Ninguno'}")
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Antecedentes:"); pdf.set_font("Arial", '', 10); pdf.multi_cell(150, 6, txt=f"{paciente['antecedentes'] or 'Ninguno'}")
    pdf.set_font("Arial", 'B', 10); pdf.cell(35, 6, txt="Diagnosticos Prev.:"); pdf.set_font("Arial", '', 10); pdf.multi_cell(150, 6, txt=f"{paciente['diagnosticos'] or 'Ninguno'}")
    pdf.ln(8)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(200, 8, txt="3. REGISTRO DE ATENCIONES MEDICAS", ln=True)
    if not historial:
        pdf.set_font("Arial", 'I', 10); pdf.cell(200, 6, txt="No hay consultas registradas para este paciente.", ln=True)
    else:
        for h in historial:
            pdf.set_font("Arial", 'B', 10); pdf.cell(30, 6, txt="Fecha/Hora:"); pdf.set_font("Arial", '', 10); pdf.cell(160, 6, txt=f"{h['fecha']} (Dr/a. {h['medico_nombre']} - {h['especialidad']})", ln=True)
            pdf.set_font("Arial", 'B', 10); pdf.cell(30, 6, txt="Diagnostico:"); pdf.set_font("Arial", '', 10); pdf.multi_cell(160, 6, txt=f"{h['diagnostico']}")
            pdf.set_font("Arial", 'B', 10); pdf.cell(30, 6, txt="Tratamiento:"); pdf.set_font("Arial", '', 10); pdf.multi_cell(160, 6, txt=f"{h['medicina']} - {h['frecuencia']} (Cant: {h['cantidad']})")
            pdf.ln(4)
            
    nombre_archivo = f"historia_clinica_{paciente_id}.pdf"
    pdf.output(nombre_archivo)
    return send_file(nombre_archivo, as_attachment=True)

@app.route('/agendar_cita', methods=['POST'])
@login_requerido
def agendar_cita():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO citas (paciente_id, medico_id, fecha) VALUES (?, ?, ?)", (request.form['paciente_id'], request.form['medico_id'], request.form['fecha'].replace('T', ' ')))
    conexion.commit(); conexion.close(); flash("✅ Cita agendada.")
    return redirect('/')

@app.route('/registrar_consulta', methods=['POST'])
@login_requerido
def registrar_consulta():
    cita_id, diagnostico, medicina, frecuencia, cantidad = request.form['cita_id'], request.form['diagnostico'], request.form['medicina'], request.form['frecuencia'], request.form['cantidad']
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO consultas (cita_id, diagnostico, medicina, frecuencia, cantidad) VALUES (?, ?, ?, ?, ?)", (cita_id, diagnostico, medicina, frecuencia, cantidad))
    cursor.execute("UPDATE citas SET estado = 'completada' WHERE id = ?", (cita_id,))
    conexion.commit()
    consulta_id = cursor.lastrowid
    conexion.close()
    flash(f"✅ Consulta registrada. <a href='/descargar_receta/{consulta_id}' target='_blank' class='btn btn-primary btn-sm ms-3 fw-bold'>📄 Imprimir Receta</a>")
    return redirect('/')

@app.route('/descargar_receta/<int:consulta_id>')
@login_requerido
def descargar_receta(consulta_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    query = """
        SELECT cons.diagnostico, cons.medicina, cons.frecuencia, cons.cantidad,
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
    pdf.set_font("Arial", 'B', 24); pdf.cell(200, 10, txt="GASTRO CLINIC", ln=True, align='C')
    pdf.set_font("Arial", 'B', 14); pdf.cell(200, 8, txt="RECETA MEDICA", ln=True, align='C')
    pdf.line(10, 40, 200, 40); pdf.ln(15)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(35, 8, txt="Paciente:"); pdf.set_font("Arial", '', 11); pdf.cell(90, 8, txt=f"{receta['paciente_nombre']}")
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(15, 8, txt="DNI:"); pdf.set_font("Arial", '', 11); pdf.cell(40, 8, txt=f"{receta['paciente_dni']}", ln=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(35, 8, txt="Fecha Consulta:"); pdf.set_font("Arial", '', 11); pdf.cell(90, 8, txt=f"{receta['fecha']}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 16); pdf.cell(200, 10, txt="Rx.", ln=True)
    pdf.set_font("Arial", 'B', 12); pdf.cell(40, 8, txt="Medicamento:"); pdf.set_font("Arial", '', 12); pdf.cell(150, 8, txt=f"{receta['medicina']}", ln=True)
    pdf.set_font("Arial", 'B', 12); pdf.cell(40, 8, txt="Cantidad:"); pdf.set_font("Arial", '', 12); pdf.cell(150, 8, txt=f"{receta['cantidad']}", ln=True)
    pdf.set_font("Arial", 'B', 12); pdf.cell(40, 8, txt="Indicaciones:"); pdf.set_font("Arial", '', 12); pdf.multi_cell(150, 8, txt=f"{receta['frecuencia']}")
    
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