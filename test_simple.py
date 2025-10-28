print("✅ Iniciando prueba...")

try:
    print("📦 Probando Flask...")
    import flask
    print("✅ Flask encontrado:", flask.__version__)
except ImportError as e:
    print("❌ Flask no encontrado:", e)

try:
    print("📦 Probando python-dotenv...")  
    from dotenv import load_dotenv
    print("✅ python-dotenv encontrado")
except ImportError as e:
    print("❌ python-dotenv no encontrado:", e)

try:
    print("📦 Probando requests...")
    import requests
    print("✅ requests encontrado:", requests.__version__)
except ImportError as e:
    print("❌ requests no encontrado:", e)

print("🏁 Prueba completada")
input("Presiona Enter para salir...")