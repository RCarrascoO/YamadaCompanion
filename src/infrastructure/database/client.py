import aiosqlite
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseClient:
    def __init__(self, db_path: str = "/shared/lilo.db"):
        self.db_path = db_path
        self._connection = None

    async def connect(self):
        if not self._connection:
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
            role TEXT DEFAULT 'user', -- 'admin', 'creator', 'user'
            relationship TEXT DEFAULT 'none' -- 'brother', 'boyfriend', 'ex', 'none'
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            channel_id INTEGER,
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
        
        # Migración simple: Intentar añadir la columna relationship si no existe (para no borrar la BD)
        try:
            await self._connection.execute("ALTER TABLE users ADD COLUMN relationship TEXT DEFAULT 'none'")
        except Exception:
            pass # La columna ya existe o error ignorado

        # Migración para conversations: añadir channel_id
        try:
            await self._connection.execute("ALTER TABLE conversations ADD COLUMN channel_id INTEGER DEFAULT 0")
        except Exception:
            pass
            
        await self._connection.commit()

    def get_connection(self):
        return self._connection

# Instancia global para ser usada en la app
db_client = DatabaseClient()
