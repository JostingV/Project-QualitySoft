from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Definir la URL de la base de datos
# SQLite crea un archivo físico llamado 'emails.db'
SQLITE_DATABASE_URL = "sqlite:///./emails.db"

# 2. Crear el motor (Engine)
# 'check_same_thread=False' es necesario solo para SQLite con FastAPI, 
# ya que FastAPI usa hilos diferentes.
engine = create_engine(
    SQLITE_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. Base declarativa para definir las clases de la tabla
Base = declarative_base()

# 4. Definición del Modelo de la Tabla (Schema)
class EmailORM(Base):
    """Mapea la tabla 'emails' en la base de datos."""
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(String, index=True)
    destinatario = Column(String)
    emisor = Column(String, index=True)
    fecha = Column(DateTime)
    codigo_smtp = Column(String, unique=True)
    contenido = Column(String)
    analisis_fraude = Column(String)

# 5. Crear la Sesión (para interactuar con la DB)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 6. Función para crear la tabla si no existe
def create_db_and_tables():
    """Crea la tabla EmailORM en la base de datos."""
    Base.metadata.create_all(bind=engine)

# 7. Función de utilidad para obtener la sesión de la DB (Dependencia para FastAPI)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()