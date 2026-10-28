import aiosqlite
import logging
import os
from src.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseClient:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or getattr(settings, 'DB_PATH', '/shared/yamada.db')
        self._connection = None

    async def connect(self):
        if not self._connection:
            # Asegurar que el directorio contenedor exista si es una ruta local
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                except Exception as e:
                    logger.warning(f"No se pudo crear directorio para base de datos {db_dir}: {e}")

            logger.info(f"Conectando a la base de datos en {self.db_path}...")
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
            await self.init_tables()
            logger.info("Base de datos conectada e inicializada.")

    async def close(self):
        if self._connection:
            await self._connection.close()
            logger.info("Conexión a base de datos cerrada.")

    async def init_tables(self):
        """Crea las tablas necesarias si no existen."""
        schema = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            display_name TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reputation INTEGER DEFAULT 0,
            role TEXT DEFAULT 'user', -- 'admin', 'vip', 'user'
            relationship TEXT DEFAULT 'none'
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            channel_id INTEGER DEFAULT 0,
            message TEXT,
            response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY,
            music_genre TEXT,
            personality_mode TEXT DEFAULT 'standard',
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        """
        await self._connection.executescript(schema)
        
        # Migración segura: añadir columna channel_id si no existe
        try:
            await self._connection.execute("ALTER TABLE conversations ADD COLUMN channel_id INTEGER DEFAULT 0")
        except Exception:
            pass
            
        await self._connection.commit()

    def get_connection(self):
        return self._connection

# Instancia global para ser usada en la app
db_client = DatabaseClient()
