import logging
from src.infrastructure.database.client import db_client

logger = logging.getLogger(__name__)

class ConversationRepository:
    async def save_interaction(self, user_id: int, channel_id: int, message: str, response: str = None):
        conn = db_client.get_connection()
        await conn.execute(
            "INSERT INTO conversations (user_id, channel_id, message, response) VALUES (?, ?, ?, ?)",
            (user_id, channel_id, message, response)
        )
        await conn.commit()

    async def get_recent_context(self, channel_id: int, limit: int = 20) -> str:
        """Recupera los últimos mensajes del canal para dar contexto."""
        conn = db_client.get_connection()
        
        # Obtenemos las últimas interacciones
        async with conn.execute(
            """
            SELECT c.message, c.response, u.display_name 
            FROM conversations c
            LEFT JOIN users u ON c.user_id = u.user_id
            WHERE c.channel_id = ?
            ORDER BY c.timestamp DESC
            LIMIT ?
            """,
            (channel_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            
        if not rows:
            return ""

        # Las filas vienen del más reciente al más antiguo, las invertimos para el prompt
        history = ""
        for row in reversed(rows):
            name = row['display_name'] or "Usuario Desconocido"
            user_msg = row['message']
            bot_resp = row['response']
            
            history += f"User ({name}): {user_msg}\n"
            if bot_resp:
                history += f"Lilo: {bot_resp}\n"
            
        return f"\n[HISTORIAL DE CONVERSACIÓN RECIENTE EN ESTE CANAL]:\n{history}\n[FIN DEL HISTORIAL]\n"
