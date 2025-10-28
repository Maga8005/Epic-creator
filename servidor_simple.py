print("🚀 Iniciando servidor simple...")

try:
    from flask import Flask
    print("✅ Flask importado correctamente")
    
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "¡Servidor funcionando!"
    
    print("📍 Servidor iniciando en http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
    
except Exception as e:
    print(f"❌ Error: {e}")
    input("Presiona Enter para salir...")
