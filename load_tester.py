import requests
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict

API_URL = "http://127.0.0.1:8000"
ENDPOINT_REGISTRO = "/emails/registro"
NUM_EMAILS_A_GENERAR = 3000
NUM_CLIENTES_UNICOS = 5

# Configuración de clientes con sus dominios y prefijos SMTP
CLIENTES_CONFIG = {
    "CLIENTE_1": {
        "dominios": [
            ("empresa1.com", "SMTP-E1"),
            ("empresa2.com", "SMTP-E2"),
            ("empresa3.com", "SMTP-E3")
        ]
    },
    "CLIENTE_2": {
        "dominios": [
            ("compania1.com", "SMTP-C1"),
            ("compania2.com", "SMTP-C2"),
            ("compania3.com", "SMTP-C3")
        ]
    },
    "CLIENTE_3": {
        "dominios": [
            ("negocio1.com", "SMTP-N1"),
            ("negocio2.com", "SMTP-N2"),
            ("negocio3.com", "SMTP-N3")
        ]
    },
    "CLIENTE_4": {
        "dominios": [
            ("firma1.com", "SMTP-F1"),
            ("firma2.com", "SMTP-F2"),
            ("firma3.com", "SMTP-F3")
        ]
    },
    "CLIENTE_5": {
        "dominios": [
            ("corporacion1.com", "SMTP-CP1"),
            ("corporacion2.com", "SMTP-CP2"),
            ("corporacion3.com", "SMTP-CP3")
        ]
    }
}

PALABRAS_FRAUDE = [
    "cuenta bloqueada", "verificación inmediata", "urgente", 
    "transferencia bancaria", "premio", "ha sido suspendida"
]

def generar_datos_aleatorios(num_emails: int) -> List[Dict]:
    """Genera datos de emails aleatorios con dominios y códigos SMTP únicos."""
    datos = []
    base_time = datetime.now()
    codigos_smtp_usados = set()
    
    for i in range(num_emails):
        # Seleccionar cliente aleatorio
        cliente_id = random.choice(list(CLIENTES_CONFIG.keys()))
        
        # Seleccionar dominio y prefijo SMTP del cliente
        dominio, prefijo_smtp = random.choice(CLIENTES_CONFIG[cliente_id]["dominios"])
        
        # Generar código SMTP único
        while True:
            sufijo = f"{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
            codigo_smtp = f"{prefijo_smtp}-{sufijo}"
            if codigo_smtp not in codigos_smtp_usados:
                codigos_smtp_usados.add(codigo_smtp)
                break
        
        # Simulación de fraude (15% de probabilidad)
        contenido = f"Cuerpo del correo {i+1}."
        if random.random() < 0.15:
            fraude_word = random.choice(PALABRAS_FRAUDE)
            contenido = f"¡ALERTA! {fraude_word}. {contenido}"
        
        email_data = {
            "cliente_id": cliente_id,
            "destinatario": f"usuario{i}@{cliente_id.lower()}.com",
            "emisor": f"remitente{i}@{dominio}",
            "codigo_smtp": codigo_smtp,
            "contenido": contenido,
            "fecha": (base_time - timedelta(minutes=i)).isoformat(),
        }
        datos.append(email_data)
    
    return datos

def run_load_test():
    """Ejecuta la prueba de carga del API."""
    print(f"Generando {NUM_EMAILS_A_GENERAR} registros de correos de prueba...")
    datos_a_enviar = generar_datos_aleatorios(NUM_EMAILS_A_GENERAR)
    
    print("\nIniciando POST masivo para la ingesta de datos...")
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{API_URL}{ENDPOINT_REGISTRO}",
            json=datos_a_enviar,
            timeout=60
        )
        response_time = time.time() - start_time
        
        if response.status_code == 201:
            print(f"✓ REGISTRO MASIVO EXITOSO (Status {response.status_code})")
            print(f"✓ Emails registrados: {len(response.json())}")
            print(f"✓ Tiempo de respuesta: {response_time:.2f} segundos")
            print(f"✓ Velocidad: {len(response.json()) / response_time:.0f} emails/segundo")
            
            # Verificar detección de fraude
            resultados = response.json()
            fraudes_detectados = sum(1 for e in resultados if 'CUIDADO' in e.get('analisis_fraude', ''))
            riesgos_moderados = sum(1 for e in resultados if 'ADVERTENCIA' in e.get('analisis_fraude', ''))
            
            print(f"\n📊 Análisis de Fraude:")
            print(f"   - Fraudes detectados: {fraudes_detectados}")
            print(f"   - Riesgos moderados: {riesgos_moderados}")
            print(f"   - Correos seguros: {len(resultados) - fraudes_detectados - riesgos_moderados}")
            
            # Mostrar ejemplo de fraude
            ejemplo_fraude = next((e for e in resultados if 'CUIDADO' in e.get('analisis_fraude', '')), None)
            if ejemplo_fraude:
                print(f"\n⚠️  Ejemplo de correo fraudulento:")
                print(f"   Cliente: {ejemplo_fraude['cliente_id']}")
                print(f"   Emisor: {ejemplo_fraude['emisor']}")
                print(f"   Contenido: {ejemplo_fraude['contenido'][:60]}...")
                print(f"   Análisis: {ejemplo_fraude['analisis_fraude']}")
        else:
            print(f"✗ ERROR DE INGESTA (Status {response.status_code}):")
            try:
                print(response.json())
            except requests.exceptions.JSONDecodeError:
                print(f"Respuesta del servidor:\n{response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"✗ ERROR DE CONEXIÓN: No se pudo conectar a {API_URL}")
        print(f"   Asegúrate de que el servidor esté corriendo con: uvicorn main:app --reload")

if __name__ == "__main__":
    run_load_test()