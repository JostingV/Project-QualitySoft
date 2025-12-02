from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database import EmailORM, create_db_and_tables, get_db

app = FastAPI(title="Análisis de Emails con API's", version="1.0.0")

@app.on_event("startup")
def startup_event():
    create_db_and_tables()

# Catálogo de dominios válidos por cliente
CATALOGO_DOMINIOS = {
    "CLIENTE_1": ["empresa1.com", "empresa2.com", "empresa3.com"],
    "CLIENTE_2": ["compania1.com", "compania2.com", "compania3.com"],
    "CLIENTE_3": ["negocio1.com", "negocio2.com", "negocio3.com"],
    "CLIENTE_4": ["firma1.com", "firma2.com", "firma3.com"],
    "CLIENTE_5": ["corporacion1.com", "corporacion2.com", "corporacion3.com"],
}

# Prefijos de códigos SMTP por dominio empresarial
PREFIJOS_SMTP_EMPRESAS = {
    "empresa1.com": "SMTP-E1",
    "empresa2.com": "SMTP-E2",
    "empresa3.com": "SMTP-E3",
    "compania1.com": "SMTP-C1",
    "compania2.com": "SMTP-C2",
    "compania3.com": "SMTP-C3",
    "negocio1.com": "SMTP-N1",
    "negocio2.com": "SMTP-N2",
    "negocio3.com": "SMTP-N3",
    "firma1.com": "SMTP-F1",
    "firma2.com": "SMTP-F2",
    "firma3.com": "SMTP-F3",
    "corporacion1.com": "SMTP-CP1",
    "corporacion2.com": "SMTP-CP2",
    "corporacion3.com": "SMTP-CP3",
}

def analizar_contenido_fraude(contenido: str) -> str:
    """Analiza el contenido del correo buscando palabras clave de fraude."""
    contenido_lower = contenido.lower()
    
    palabras_fraude = [
        "cuenta bloqueada", "verificación inmediata", "actualice su contraseña", 
        "premio", "urgente", "pago fallido", "ha sido suspendida", "transferencia bancaria"
    ]
    
    riesgo_alto = sum(1 for palabra in palabras_fraude if palabra in contenido_lower)
    
    if riesgo_alto >= 2:
        return "CUIDADO, PROBABLEMENTE SEA FRAUDE"
    elif riesgo_alto == 1:
        return "ADVERTENCIA, RIESGO MODERADO"
    return "EL CORREO ES SEGURO"

def extraer_dominio(email: str) -> str:
    """Extrae el dominio de una dirección de email."""
    return email.split('@')[-1].lower() if '@' in email else ""

class EmailRegistro(BaseModel):
    cliente_id: str
    destinatario: str
    emisor: str
    fecha: datetime
    codigo_smtp: str
    contenido: str
    analisis_fraude: Optional[str] = None

class EmailDB(EmailRegistro):
    id: int
    analisis_fraude: str

    class Config:
        from_attributes = True

@app.post("/emails/registro", status_code=status.HTTP_201_CREATED, response_model=List[EmailDB])
async def registrar_emails_masivo(
    emails: List[EmailRegistro],
    db: Session = Depends(get_db)
):
    """Registra emails masivamente validando dominio y código SMTP."""
    nuevos_emails_guardados = []
    
    for email in emails:
        # Validar que el cliente existe
        dominios_permitidos = CATALOGO_DOMINIOS.get(email.cliente_id)
        if dominios_permitidos is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cliente ID '{email.cliente_id}' no está registrado."
            )
        
        # Extraer y validar dominio del emisor
        dominio_emisor = extraer_dominio(email.emisor)
        if dominio_emisor not in dominios_permitidos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dominio '{dominio_emisor}' no está permitido para el cliente '{email.cliente_id}'."
            )
        
        # Validar prefijo del código SMTP
        prefijo_esperado = PREFIJOS_SMTP_EMPRESAS.get(dominio_emisor)
        if prefijo_esperado is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dominio '{dominio_emisor}' no tiene un prefijo SMTP configurado."
            )
        
        if not email.codigo_smtp.startswith(prefijo_esperado):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Código SMTP inválido para el dominio '{dominio_emisor}'. Debe iniciar con '{prefijo_esperado}'."
            )
        
        # Análisis de fraude
        estado_fraude = analizar_contenido_fraude(email.contenido)
        
        # Preparar datos
        email_data = email.dict()
        email_data['cliente_id'] = email.cliente_id.upper()
        email_data['analisis_fraude'] = estado_fraude
        
        db_email = EmailORM(**email_data)
        db.add(db_email)
        nuevos_emails_guardados.append(db_email)

    db.commit()
    
    for e in nuevos_emails_guardados:
        db.refresh(e)
    
    return [EmailDB.from_orm(e) for e in nuevos_emails_guardados]

@app.get("/emails/busqueda", response_model=List[EmailDB])
async def buscar_emails(
    cliente_id: str,
    contenido: Optional[str] = None,
    emisor: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """Busca emails filtrando por cliente_id (obligatorio) y otros parámetros opcionales."""
    query = db.query(EmailORM).filter(EmailORM.cliente_id == cliente_id)
    
    if contenido and contenido.strip():
        contenido_lower = contenido.strip().lower()
        query = query.filter(EmailORM.contenido.like(f"%{contenido_lower}%"))

    if emisor:
        query = query.filter(EmailORM.emisor == emisor)

    skip = (page - 1) * page_size
    resultados_filtrados = query.offset(skip).limit(page_size).all()

    return resultados_filtrados