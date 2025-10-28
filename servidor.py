print("🏃 Iniciando Epic Creator con OAuth...")

# Importaciones
from flask import Flask, request, jsonify, redirect, session, render_template_string
import os
from dotenv import load_dotenv
import requests
import base64
import time
import secrets
import hashlib

print("✅ Librerías importadas")

# Cargar variables de entorno
print("📄 Cargando archivo .env...")
load_dotenv()

# Configuración
JIRA_URL = os.getenv('JIRA_URL')
JIRA_EMAIL = os.getenv('JIRA_EMAIL') 
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

# Configuración OAuth para Claude
OAUTH_CLIENT_ID = os.getenv('OAUTH_CLIENT_ID', 'epic-creator-claude')
OAUTH_CLIENT_SECRET = os.getenv('OAUTH_CLIENT_SECRET', secrets.token_urlsafe(32))

print(f"📧 Email: {JIRA_EMAIL}")
print(f"🌐 URL: {JIRA_URL}")
print(f"🔑 Token: ***{JIRA_API_TOKEN[-4:] if JIRA_API_TOKEN else 'NO CONFIGURADO'}")
print(f"🔐 OAuth Client ID: {OAUTH_CLIENT_ID}")

# Crear app Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))

# Almacenamiento temporal de códigos y tokens (en producción usar Redis/DB)
authorization_codes = {}
access_tokens = {}

@app.route('/')
def inicio():
    return """
    <h1>🚀 Servidor Epic Creator funcionando!</h1>
    <h3>📊 Endpoints disponibles:</h3>
    <ul>
        <li><a href="/test-jira">/test-jira</a> - Probar conexión</li>
        <li><a href="/test-crear-epica">/test-crear-epica</a> - Crear épica de prueba</li>
        <li><a href="/crear-epica-desde-claude">/crear-epica-desde-claude</a> - Endpoint para Claude</li>
    </ul>
    <h3>🔐 OAuth Endpoints:</h3>
    <ul>
        <li>/oauth/authorize - Autorización OAuth</li>
        <li>/oauth/token - Intercambio de tokens</li>
        <li>/.well-known/ai-plugin.json - Manifest para Claude</li>
    </ul>
    <p><strong>✅ Estado:</strong> Activo</p>
    """

# ============= OAUTH ENDPOINTS =============

@app.route('/.well-known/ai-plugin.json')
def ai_plugin_manifest():
    """Manifest que Claude lee para entender cómo conectarse"""
    base_url = request.host_url.rstrip('/')
    
    return jsonify({
        "schema_version": "v1",
        "name_for_human": "Epic Creator",
        "name_for_model": "epic_creator",
        "description_for_human": "Crea épicas y historias en Jira directamente desde Claude",
        "description_for_model": "Permite crear épicas y user stories en Jira. Usa el endpoint /crear-epica-desde-claude con formato JSON.",
        "auth": {
            "type": "oauth",
            "client_url": f"{base_url}/oauth/authorize",
            "authorization_url": f"{base_url}/oauth/token",
            "authorization_content_type": "application/json",
            "scope": "create_epic create_story"
        },
        "api": {
            "type": "openapi",
            "url": f"{base_url}/openapi.json"
        },
        "logo_url": f"{base_url}/logo.png",
        "contact_email": JIRA_EMAIL,
        "legal_info_url": f"{base_url}"
    })

@app.route('/openapi.json')
def openapi_spec():
    """OpenAPI spec que describe los endpoints disponibles"""
    base_url = request.host_url.rstrip('/')
    
    return jsonify({
        "openapi": "3.0.0",
        "info": {
            "title": "Epic Creator API",
            "version": "1.0.0",
            "description": "API para crear épicas y historias en Jira"
        },
        "servers": [{"url": base_url}],
        "paths": {
            "/crear-epica-desde-claude": {
                "post": {
                    "summary": "Crear épica con historias",
                    "operationId": "crearEpica",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["epic_title"],
                                    "properties": {
                                        "epic_title": {
                                            "type": "string",
                                            "description": "Título de la épica"
                                        },
                                        "epic_description": {
                                            "type": "string",
                                            "description": "Descripción de la épica"
                                        },
                                        "stories": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Lista de historias de usuario"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Épica creada exitosamente",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "epic": {"type": "object"},
                                            "stories": {"type": "array"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    })

@app.route('/oauth/authorize')
def oauth_authorize():
    """Página de autorización OAuth - Claude redirige aquí"""
    
    # Obtener parámetros de la petición
    client_id = request.args.get('client_id')
    redirect_uri = request.args.get('redirect_uri')
    state = request.args.get('state')
    scope = request.args.get('scope', '')
    
    print(f"🔐 Solicitud OAuth recibida:")
    print(f"   Client ID: {client_id}")
    print(f"   Redirect URI: {redirect_uri}")
    print(f"   State: {state}")
    
    # Validar client_id
    if client_id != OAUTH_CLIENT_ID:
        return "❌ Client ID inválido", 400
    
    # Validar redirect_uri (Claude usa dominios específicos)
    if not redirect_uri or not redirect_uri.startswith('https://claude.ai'):
        return "❌ Redirect URI inválido", 400
    
    # Generar código de autorización
    auth_code = secrets.token_urlsafe(32)
    
    # Guardar código temporalmente (expira en 10 minutos)
    authorization_codes[auth_code] = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'timestamp': time.time(),
        'scope': scope
    }
    
    print(f"✅ Código de autorización generado: {auth_code[:10]}...")
    
    # Redirigir de vuelta a Claude con el código
    callback_url = f"{redirect_uri}?code={auth_code}&state={state}"
    return redirect(callback_url)

@app.route('/oauth/token', methods=['POST'])
def oauth_token():
    """Intercambiar código de autorización por access token"""
    
    data = request.get_json() or request.form.to_dict()
    
    grant_type = data.get('grant_type')
    code = data.get('code')
    client_id = data.get('client_id')
    client_secret = data.get('client_secret')
    redirect_uri = data.get('redirect_uri')
    
    print(f"🔑 Solicitud de token:")
    print(f"   Grant type: {grant_type}")
    print(f"   Code: {code[:10] if code else None}...")
    print(f"   Client ID: {client_id}")
    
    # Validar grant_type
    if grant_type != 'authorization_code':
        return jsonify({'error': 'unsupported_grant_type'}), 400
    
    # Validar código de autorización
    if code not in authorization_codes:
        return jsonify({'error': 'invalid_grant', 'error_description': 'Código inválido o expirado'}), 400
    
    auth_data = authorization_codes[code]
    
    # Verificar que no haya expirado (10 minutos)
    if time.time() - auth_data['timestamp'] > 600:
        del authorization_codes[code]
        return jsonify({'error': 'invalid_grant', 'error_description': 'Código expirado'}), 400
    
    # Validar client_id
    if client_id != auth_data['client_id']:
        return jsonify({'error': 'invalid_client'}), 400
    
    # Generar access token
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)
    
    # Guardar token (en producción: guardar en DB con expiración)
    access_tokens[access_token] = {
        'client_id': client_id,
        'scope': auth_data['scope'],
        'timestamp': time.time()
    }
    
    # Eliminar código usado
    del authorization_codes[code]
    
    print(f"✅ Access token generado: {access_token[:10]}...")
    
    # Responder con tokens
    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 3600,
        'refresh_token': refresh_token,
        'scope': auth_data['scope']
    })

def verify_token():
    """Middleware para verificar el access token"""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.replace('Bearer ', '')
    
    if token not in access_tokens:
        return None
    
    token_data = access_tokens[token]
    
    # Verificar que no haya expirado (1 hora)
    if time.time() - token_data['timestamp'] > 3600:
        del access_tokens[token]
        return None
    
    return token_data

# ============= ENDPOINTS ORIGINALES =============

@app.route('/test-jira')
def test_jira():
    if not JIRA_EMAIL or not JIRA_API_TOKEN:
        return "<h2>❌ Error: Credenciales no configuradas</h2>"
    
    try:
        credentials = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {"Authorization": f"Basic {encoded}"}
        
        response = requests.get(f"{JIRA_URL}/rest/api/3/myself", headers=headers, timeout=15)
        
        if response.status_code == 200:
            user_data = response.json()
            return f"""
            <h2>✅ ¡Conexión exitosa!</h2>
            <p><strong>Usuario:</strong> {user_data.get('displayName')}</p>
            <p><strong>Email:</strong> {user_data.get('emailAddress')}</p>
            """
        else:
            return f"<h2>❌ Error {response.status_code}</h2>"
            
    except Exception as e:
        return f"<h2>❌ Error: {str(e)}</h2>"

@app.route('/test-crear-epica')
def test_crear_epica():
    return '''
    <h2>🧪 Crear Épica de Prueba</h2>
    <button onclick="crearEpica()">Crear Epic Creator Tool</button>
    <div id="resultado"></div>
    
    <script>
    function crearEpica() {
        document.getElementById('resultado').innerHTML = '⏳ Creando...';
        
        fetch('/crear-epica-real', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                epic: {
                    summary: 'Epic Creator Tool - Automatización con Claude y Jira'
                }
            })
        })
        .then(response => response.json())
        .then(data => {
            if(data.status === 'success') {
                document.getElementById('resultado').innerHTML = 
                    `<h3>✅ ${data.mensaje}</h3>
                     <p><a href="${data.epic_url}" target="_blank">🔗 Ver en Jira</a></p>`;
            } else {
                document.getElementById('resultado').innerHTML = `<h3>❌ ${data.mensaje}</h3>`;
            }
        });
    }
    </script>
    '''

@app.route('/crear-epica-real', methods=['POST'])
def crear_epica_real():
    try:
        datos = request.get_json()
        if not datos:
            return jsonify({'status': 'error', 'mensaje': 'No se recibieron datos'})
        
        epic_data = datos.get('epic')
        print(f"🚀 Creando: {epic_data.get('summary')}")
        
        credentials = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "fields": {
                "project": {"key": "BIZ"},
                "summary": epic_data.get('summary'),
                "issuetype": {"name": "Epic"}
            }
        }
        
        response = requests.post(
            f"{JIRA_URL}/rest/api/3/issue",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 201:
            result = response.json()
            epic_key = result['key']
            return jsonify({
                'status': 'success',
                'mensaje': f'Épica {epic_key} creada',
                'epic_key': epic_key,
                'epic_url': f"{JIRA_URL}/browse/{epic_key}"
            })
        else:
            return jsonify({
                'status': 'error',
                'mensaje': f'Error {response.status_code}: {response.text}'
            })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'mensaje': f'Error: {str(e)}'
        })

@app.route('/crear-epica-desde-claude', methods=['GET', 'POST'])
def crear_epica_desde_claude():
    """Endpoint para recibir épicas desde Claude - AHORA CON OAUTH"""
    
    if request.method == 'GET':
        return '''
        <h1>🔗 Epic Creator - Endpoint para Claude Projects</h1>
        <h2>📡 Estado: Activo con OAuth</h2>
        <p><strong>Método:</strong> POST</p>
        <p><strong>Autenticación:</strong> Bearer Token (OAuth 2.0)</p>
        <p><strong>URL:</strong> /crear-epica-desde-claude</p>
        
        <h3>📋 Formato JSON esperado:</h3>
        <pre>{
  "epic_title": "Título de la épica",
  "epic_description": "Descripción opcional",
  "stories": [
    "Historia 1",
    "Historia 2"
  ]
}</pre>
        
        <a href="/">← Volver al inicio</a>
        '''
    
    # Verificar token OAuth
    token_data = verify_token()
    if not token_data:
        return jsonify({'error': 'Token inválido o expirado'}), 401
    
    print(f"✅ Token válido para client: {token_data['client_id']}")
    
    try:
        if not request.json:
            return jsonify({"error": "No se recibieron datos JSON"}), 400
        
        data = request.json
        
        if not data.get('epic_title'):
            return jsonify({"error": "epic_title es requerido"}), 400
            
        credentials = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}",
            'Content-Type': 'application/json'
        }
        
        epic_payload = {
            "fields": {
                "project": {"key": "BIZ"},
                "summary": data['epic_title'],
                "issuetype": {"name": "Epic"}
            }
        }
        
        if data.get('epic_description'):
            epic_payload["fields"]["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": data['epic_description']
                            }
                        ]
                    }
                ]
            }
        
        print(f"🚀 Creando épica desde Claude: {data['epic_title']}")
        
        response = requests.post(f"{JIRA_URL}/rest/api/3/issue", 
                               json=epic_payload, 
                               headers=headers)
        
        if response.status_code != 201:
            return jsonify({
                "error": f"Error creando épica: {response.status_code}",
                "details": response.text
            }), 400
        
        epic_response = response.json()
        epic_key = epic_response['key']
        print(f"✅ Épica creada: {epic_key}")
        
        created_stories = []
        if data.get('stories') and len(data['stories']) > 0:
            print(f"📝 Creando {len(data['stories'])} historias...")
            created_stories = crear_historias_para_claude(epic_key, data['stories'], headers)
        
        result = {
            "status": "success",
            "message": "Épica e historias creadas exitosamente",
            "epic": {
                "key": epic_key,
                "title": data['epic_title'],
                "url": f"{JIRA_URL}/browse/{epic_key}"
            },
            "stories": created_stories,
            "total_created": f"1 épica + {len(created_stories)} historias"
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error en crear_epica_desde_claude: {str(e)}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

def crear_historias_para_claude(epic_key, stories_data, headers):
    """Crear historias optimizada para Claude Projects"""
    created_stories = []
    
    for i, story in enumerate(stories_data, 1):
        print(f"📝 Historia {i}/{len(stories_data)}: {story}")
        
        story_payload = {
            "fields": {
                "project": {"key": "BIZ"},
                "summary": story,
                "issuetype": {"name": "Story"},
                "parent": {"key": epic_key}
            }
        }
        
        if i > 1:
            time.sleep(1)
            
        try:
            response = requests.post(f"{JIRA_URL}/rest/api/3/issue", 
                                   json=story_payload, 
                                   headers=headers)
            
            if response.status_code == 201:
                story_data = response.json()
                created_stories.append({
                    'key': story_data['key'],
                    'title': story,
                    'url': f"{JIRA_URL}/browse/{story_data['key']}"
                })
                print(f"✅ Historia creada: {story_data['key']}")
            else:
                print(f"❌ Error en historia: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error en historia: {str(e)}")
    
    return created_stories

# Iniciar servidor
if __name__ == '__main__':
    print("\n🚀 Servidor Epic Creator con OAuth iniciado!")
    print("📍 Endpoints OAuth configurados:")
    print("   🔐 /.well-known/ai-plugin.json")
    print("   🔐 /oauth/authorize")
    print("   🔐 /oauth/token")
    print("   📡 /crear-epica-desde-claude")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)