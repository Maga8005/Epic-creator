print("🏃 Iniciando Epic Creator...")

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

# Configuración
JIRA_URL = os.getenv('JIRA_URL')
JIRA_EMAIL = os.getenv('JIRA_EMAIL') 
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

print(f"📧 Email: {JIRA_EMAIL}")
print(f"🌐 URL: {JIRA_URL}")
print(f"🔑 Token: ***{JIRA_API_TOKEN[-4:] if JIRA_API_TOKEN else 'NO CONFIGURADO'}")

# Crear app Flask
app = Flask(__name__)

@app.route('/')
def inicio():
    return """
    <h1>🚀 Servidor Epic Creator funcionando!</h1>
    <h3>📊 Endpoints disponibles:</h3>
    <ul>
        <li><a href="/test-jira">/test-jira</a> - Probar conexión</li>
        <li><a href="/test-crear-epica">/test-crear-epica</a> - Crear épica de prueba</li>
        <li><a href="/test-epica-completa">/test-epica-completa</a> → Demo completa</li>
    </ul>
    <p><strong>✅ Estado:</strong> Activo</p>
    """

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
        
        # Credenciales
        credentials = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json"
        }
        
        # Payload simple
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

def crear_historias_asociadas(epic_key, stories_data):
    """Crear historias asociadas a una épica con rate limiting"""
    
    credentials = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}",
        'Content-Type': 'application/json'
    }

    created_stories = []
    
    for i, story in enumerate(stories_data, 1):
        story_payload = {
    "fields": {
        "project": {"key": "BIZ"},
        "summary": story.get('summary'),
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": story.get('description', '')
                        }
                    ]
                }
            ]
        } if story.get('description') else None,
        "issuetype": {"name": "Story"},
        "parent": {"key": epic_key}
    }
}
        
        # Rate limiting - esperar entre historias
        if i > 1:
            time.sleep(2)  # 2 segundos entre historias
            
        try:
            response = requests.post(f"{JIRA_URL}/rest/api/3/issue", 
                                   json=story_payload, 
                                   headers=headers)
            
            if response.status_code == 201:
                story_data = response.json()
                created_stories.append({
                    'key': story_data['key'],
                    'summary': story.get('summary'),
                    'url': f"{JIRA_URL}/browse/{story_data['key']}"
                })
                print(f"✅ Historia creada: {story_data['key']}")
            else:
                print(f"❌ Error creando historia: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error en historia: {str(e)}")
    
    return created_stories

# Nuevo endpoint para prueba completa
# @app.route('/test-epica-completa')
def test_epica_completa():
    """Crear una épica de prueba con historias asociadas"""

    credentials = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}",
        'Content-Type': 'application/json'
    }

    # Datos de prueba - épica completa
    epic_data = {
        "summary": "Sistema de Notificaciones Push - DEMO",
        "description": "Implementar sistema completo de notificaciones push para la aplicación móvil",
        "stories": [
            {
                "summary": "Investigar proveedores de push notifications (FCM, APNs)",
                "description": "Analizar opciones técnicas y costos de implementación"
            },
            {
                "summary": "Diseñar arquitectura del sistema de notificaciones",
                "description": "Definir flujo de datos y componentes necesarios"
            },
            {
                "summary": "Implementar backend para envío de notificaciones",
                "description": "API REST para gestión y envío de push notifications"
            },
            {
                "summary": "Integrar SDK en app móvil",
                "description": "Configurar Firebase/APNs en la aplicación cliente"
            },
            {
                "summary": "Crear panel de administración",
                "description": "Interface para que marketing pueda enviar notificaciones"
            },
            {
                "summary": "Testing y QA del sistema completo",
                "description": "Pruebas de extremo a extremo del flujo de notificaciones"
            }
        ]
    }
    
    try:
        # 1. Crear la épica
        print("🚀 Creando épica de demo...")
        epic_payload = {
    "fields": {
        "project": {"key": "BIZ"},
        "summary": epic_data["summary"],
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": epic_data["description"]
                        }
                    ]
                }
            ]
        },
        "issuetype": {"name": "Epic"}
    }
}
        
        response = requests.post(f"{JIRA_URL}/rest/api/3/issue", 
                               json=epic_payload, 
                               headers=headers)
        
        if response.status_code != 201:
            return f"❌ Error creando épica: {response.status_code} - {response.text}"
        
        epic_response = response.json()
        epic_key = epic_response['key']
        print(f"✅ Épica creada: {epic_key}")
        
        # 2. Crear historias asociadas
        print("📚 Creando historias asociadas...")
        created_stories = crear_historias_asociadas(epic_key, epic_data["stories"])
        
        # 3. Resultado
        result = f"""
        <h1>🎉 DEMO COMPLETA EXITOSA</h1>
        <h2>📋 Épica Creada:</h2>
        <p><strong>{epic_key}</strong>: {epic_data["summary"]}</p>
        <p><a href="{JIRA_URL}/browse/{epic_key}" target="_blank">Ver en Jira →</a></p>
        
        <h2>📝 Historias Creadas ({len(created_stories)}):</h2>
        <ul>
        """
        
        for story in created_stories:
            result += f'<li><strong>{story["key"]}</strong>: {story["summary"]} <a href="{story["url"]}" target="_blank">→</a></li>'
        
        result += """
        </ul>
        <p><strong>🎯 Total:</strong> 1 épica + {len} historias creadas exitosamente</p>
        """.replace("{len}", str(len(created_stories)))
        
        return result
        
    except Exception as e:
        return f"❌ Error en demo completa: {str(e)}"
    

@app.route('/crear-epica-desde-claude', methods=['GET', 'POST'])
def crear_epica_desde_claude():
    """Endpoint para recibir épicas desde Claude Projects"""
    
    # Si es GET, mostrar información
    if request.method == 'GET':
        return '''
        <h1>🔗 Epic Creator - Endpoint para Claude Projects</h1>
        <h2>📡 Estado: Activo</h2>
        <p><strong>Método:</strong> POST</p>
        <p><strong>URL:</strong> /crear-epica-desde-claude</p>
        
        <h3>📋 Formato JSON esperado:</h3>
        <pre>{
  "epic_title": "Título de la épica",
  "epic_description": "Descripción opcional",
  "stories": [
    "Historia 1",
    "Historia 2", 
    "Historia 3"
  ]
}</pre>
        
        <h3>🧪 Para probar:</h3>
        <p>Envía POST con JSON al mismo URL</p>
        
        <a href="/">← Volver al inicio</a>
        '''
    
    # Si es POST, procesar la épica
    try:
        # 1. Validar que lleguen datos
        if not request.json:
            return {"error": "No se recibieron datos JSON"}, 400
        
        data = request.json
        
        # 2. Validar campos requeridos
        if not data.get('epic_title'):
            return {"error": "epic_title es requerido"}, 400
            
        # 3. Configurar autenticación (misma que funciona)
        credentials = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded}",
            'Content-Type': 'application/json'
        }
        
        # 4. Crear la épica
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
        
        print(f"🚀 Creando épica desde Claude: {data['epic_title']}")
        
        # Crear épica en Jira
        response = requests.post(f"{JIRA_URL}/rest/api/3/issue", 
                               json=epic_payload, 
                               headers=headers)
        
        if response.status_code != 201:
            return {
                "error": f"Error creando épica: {response.status_code}",
                "details": response.text
            }, 400
        
        epic_response = response.json()
        epic_key = epic_response['key']
        print(f"✅ Épica creada: {epic_key}")
        
        # 5. Crear historias si vienen
        created_stories = []
        if data.get('stories') and len(data['stories']) > 0:
            print(f"📝 Creando {len(data['stories'])} historias...")
            created_stories = crear_historias_para_claude(epic_key, data['stories'], headers)
        
        # 6. Respuesta para Claude
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
        
        return result
        
    except Exception as e:
        print(f"❌ Error en crear_epica_desde_claude: {str(e)}")
        return {"error": f"Error interno: {str(e)}"}, 500

def crear_historias_para_claude(epic_key, stories_data, headers):
    """Crear historias optimizada para Claude Projects"""
    created_stories = []
    
    for i, story in enumerate(stories_data, 1):
        print(f"📝 Historia {i}/{len(stories_data)}: {story}")
        
        story_payload = {
            "fields": {
                "project": {"key": "BIZ"},
                "summary": story,  # Claude envía strings simples
                "issuetype": {"name": "Story"},
                "parent": {"key": epic_key}
            }
        }
        
        # Rate limiting
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
    print("\n🚀 Servidor iniciado!")
    print("📍 http://127.0.0.1:5000")
    print("🧪 http://127.0.0.1:5000/test-crear-epica")
    # print("🎭 http://127.0.0.1:5000/test-epica-completa")
    print("🔗 http://127.0.0.1:5000/crear-epica-desde-claude")
    #app.run(debug=True, host='127.0.0.1', port=5000)
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
