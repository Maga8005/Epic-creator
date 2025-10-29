print("🏃 Iniciando Epic Creator con API Key...")

# Importaciones
from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import requests
import base64
import time

print("✅ Librerías importadas")

# Cargar variables de entorno
print("📄 Cargando archivo .env...")
load_dotenv()

# Configuración Jira
JIRA_URL = os.getenv('JIRA_URL')
JIRA_EMAIL = os.getenv('JIRA_EMAIL') 
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

# API Key para autenticación simple
API_KEY = os.getenv('API_KEY', 'epic-creator-2024-key')

print(f"📧 Email: {JIRA_EMAIL}")
print(f"🌐 URL: {JIRA_URL}")
print(f"🔑 Jira Token: ***{JIRA_API_TOKEN[-4:] if JIRA_API_TOKEN else 'NO CONFIGURADO'}")
print(f"🔐 API Key: ***{API_KEY[-4:] if API_KEY else 'NO CONFIGURADO'}")

# Crear app Flask
app = Flask(__name__)

def verificar_api_key():
    """Verifica que la petición tenga una API key válida"""
    api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if api_key != API_KEY:
        return False
    return True

@app.route('/')
def inicio():
    return """
    <h1>🚀 Servidor Epic Creator funcionando!</h1>
    <h2>Autenticación: API Key</h2>
    
    <h3>📊 Endpoints disponibles:</h3>
    <ul>
        <li><a href="/test-jira">/test-jira</a> - Probar conexión a Jira</li>
        <li>/crear-epica - Crear épica con historias (requiere API Key)</li>
    </ul>
    
    <h3>🔐 Autenticación:</h3>
    <p>Incluye el header: <code>X-API-Key: tu-api-key</code></p>
    <p>O: <code>Authorization: Bearer tu-api-key</code></p>
    
    <h3>📋 Formato de petición a /crear-epica:</h3>
    <pre>
POST /crear-epica
Headers: 
  X-API-Key: tu-api-key
  Content-Type: application/json

Body:
{
  "epic_title": "Título de la épica",
  "epic_description": "Descripción opcional",
  "stories": [
    "Historia 1",
    "Historia 2",
    "Historia 3"
  ]
}
    </pre>
    
    <p><strong>✅ Estado:</strong> Activo</p>
    """

@app.route('/test-jira')
def test_jira():
    """Probar conexión a Jira"""
    if not JIRA_EMAIL or not JIRA_API_TOKEN:
        return "<h2>❌ Error: Credenciales de Jira no configuradas</h2>"
    
    try:
        credentials = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {"Authorization": f"Basic {encoded}"}
        
        response = requests.get(f"{JIRA_URL}/rest/api/3/myself", headers=headers, timeout=15)
        
        if response.status_code == 200:
            user_data = response.json()
            return f"""
            <h2>✅ ¡Conexión a Jira exitosa!</h2>
            <p><strong>Usuario:</strong> {user_data.get('displayName')}</p>
            <p><strong>Email:</strong> {user_data.get('emailAddress')}</p>
            """
        else:
            return f"<h2>❌ Error {response.status_code}</h2>"
            
    except Exception as e:
        return f"<h2>❌ Error: {str(e)}</h2>"

@app.route('/crear-epica', methods=['POST'])
def crear_epica():
    """Endpoint principal para crear épicas desde Claude"""
    
    # Verificar API Key
    if not verificar_api_key():
        return jsonify({
            "error": "No autorizado",
            "message": "API Key inválida o ausente. Incluye el header X-API-Key o Authorization: Bearer"
        }), 401
    
    print(f"✅ API Key válida - Procesando petición...")
    
    try:
        # Obtener datos
        if not request.json:
            return jsonify({"error": "No se recibieron datos JSON"}), 400
        
        data = request.json
        print(f"📥 Datos recibidos: {data}")
        
        # Validar campo requerido
        if not data.get('epic_title'):
            return jsonify({"error": "epic_title es requerido"}), 400
        
        # Configurar autenticación para Jira
        credentials = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}",
            'Content-Type': 'application/json'
        }
        
        # Crear payload para la épica
        epic_payload = {
            "fields": {
                "project": {"key": "BIZ"},
                "summary": data['epic_title'],
                "issuetype": {"name": "Epic"}
            }
        }
        
        # Agregar descripción si viene
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
        
        print(f"🚀 Creando épica: {data['epic_title']}")
        
        # Crear épica en Jira
        response = requests.post(
            f"{JIRA_URL}/rest/api/3/issue", 
            json=epic_payload, 
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 201:
            error_msg = f"Error creando épica: {response.status_code}"
            print(f"❌ {error_msg}")
            print(f"   Respuesta: {response.text}")
            return jsonify({
                "error": error_msg,
                "details": response.text
            }), 400
        
        epic_response = response.json()
        epic_key = epic_response['key']
        print(f"✅ Épica creada: {epic_key}")
        
        # Crear historias si vienen
        created_stories = []
        if data.get('stories') and len(data['stories']) > 0:
            print(f"📝 Creando {len(data['stories'])} historias...")
            created_stories = crear_historias(epic_key, data['stories'], headers)
        
        # Respuesta exitosa
        result = {
            "status": "success",
            "message": f"✅ Épica {epic_key} creada exitosamente",
            "epic": {
                "key": epic_key,
                "title": data['epic_title'],
                "url": f"{JIRA_URL}/browse/{epic_key}"
            },
            "stories": created_stories,
            "summary": f"Se creó 1 épica con {len(created_stories)} historias"
        }
        
        print(f"🎉 Proceso completado exitosamente")
        return jsonify(result)
        
    except Exception as e:
        error_msg = f"Error interno: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

def crear_historias(epic_key, stories_data, headers):
    """Crear historias asociadas a una épica"""
    created_stories = []
    
    for i, story in enumerate(stories_data, 1):
        print(f"   📝 Historia {i}/{len(stories_data)}: {story[:50]}...")
        
        story_payload = {
            "fields": {
                "project": {"key": "BIZ"},
                "summary": story,
                "issuetype": {"name": "Story"},
                "parent": {"key": epic_key}
            }
        }
        
        # Rate limiting - esperar entre historias
        if i > 1:
            time.sleep(1)
        
        try:
            response = requests.post(
                f"{JIRA_URL}/rest/api/3/issue", 
                json=story_payload, 
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 201:
                story_data = response.json()
                created_stories.append({
                    'key': story_data['key'],
                    'title': story,
                    'url': f"{JIRA_URL}/browse/{story_data['key']}"
                })
                print(f"   ✅ {story_data['key']} creada")
            else:
                print(f"   ❌ Error {response.status_code} en historia")
                
        except Exception as e:
            print(f"   ❌ Error en historia: {str(e)}")
    
    return created_stories

# Health check para Render
@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "epic-creator"}), 200

# Iniciar servidor
if __name__ == '__main__':
    print("\n🚀 Servidor Epic Creator iniciado!")
    print(f"📍 Endpoint principal: /crear-epica")
    print(f"🔐 Autenticación: API Key")
    print(f"🧪 Prueba conexión Jira: /test-jira")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)