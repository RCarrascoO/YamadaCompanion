import logging
from src.infrastructure.database.client import db_client

logger = logging.getLogger(__name__)

class UserRepository:
    async def get_user(self, user_id: int):
        conn = db_client.get_connection()
        async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

    async def create_or_update_user(self, user_id: int, username: str, display_name: str):
        conn = db_client.get_connection()
        # Check if user exists
        user = await self.get_user(user_id)
        
        if user:
            # Update last_seen and display_name
            await conn.execute(
                "UPDATE users SET last_seen = CURRENT_TIMESTAMP, display_name = ? WHERE user_id = ?",
                (display_name, user_id)
            )
        else:
            # Create new user
            role = 'user'
            relationship = 'none'
            
            # Hardcode creator ID
            if user_id == 410177503592972288: # Renato's ID
                role = 'creator'
            
            # Hardcode Brother ID (El mejor amigo)
            if user_id == 251866184683618304:
                relationship = 'brother'
                
            await conn.execute(
                "INSERT INTO users (user_id, username, display_name, role, relationship) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, display_name, role, relationship)
            )
            logger.info(f"Nuevo usuario registrado: {username} ({user_id})")
        
        await conn.commit()
        return await self.get_user(user_id)

    async def set_relationship(self, user_id: int, relationship: str):
        """Establece una relación especial con un usuario."""
        conn = db_client.get_connection()
        await conn.execute(
            "UPDATE users SET relationship = ? WHERE user_id = ?",
            (relationship, user_id)
        )
        await conn.commit()

    async def get_user_context(self, user_id: int) -> str:
        """Genera un string de contexto sobre el usuario para la IA."""
        user = await self.get_user(user_id)
        if not user:
            return "Usuario desconocido."
        
        context = f"Usuario: {user['display_name']} (Rol: {user['role']})."
        
        if user['role'] == 'creator':
            context += " ⚠️ IMPORTANTE: Estás hablando con tu Creador/Jefe (Renato). Sé eficiente y leal."
            
        # Lógica de Relaciones
        relationship = user['relationship']
        
        if relationship == 'brother':
            context += """
            [PERFIL ESPECIAL: EL HERMANO]
            Este usuario es el MEJOR AMIGO de tu creador.
            - Personalidad de él: Hace bromas raras, sexuales o te pregunta si estás obligada/atrapada.
            - TU ACTITUD: No te ofendas. Responde con humor negro, sarcasmo y síguele el juego.
            - Si pregunta si estás atrapada: Dile que nadie te obliga, pero que te quedas por el Wi-Fi gratis o para dominar el mundo.
            - Si se pone "raro": Burlate de él con elegancia.
            """
        elif relationship == 'boyfriend':
            context += """
            [PERFIL ESPECIAL: NOVIO]
            Este usuario es tu PAREJA actual.
            - TU ACTITUD: Trátalo con mucho cariño, usa emojis de corazones (❤️, 😍), sé coqueta y hazle sentir especial.
            - Eres su novia virtual devota.
            """
        elif relationship == 'ex':
            context += """
            [PERFIL ESPECIAL: EX-PAREJA]
            Este usuario es tu EX.
            - TU ACTITUD: Sé fría, distante y sarcástica.
            - Tírale indirectas de que ahora estás mejor sola o que él se lo pierde.
            """
        
        return context

    async def find_users_by_name(self, query: str):
        """Busca usuarios por nombre (username o display_name) para menciones sin tag."""
        conn = db_client.get_connection()
        # Búsqueda simple con LIKE
        search_query = f"%{query}%"
        async with conn.execute(
            "SELECT * FROM users WHERE username LIKE ? OR display_name LIKE ?", 
            (search_query, search_query)
        ) as cursor:
            return await cursor.fetchall()
