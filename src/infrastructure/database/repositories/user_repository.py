import logging
from src.core.config import settings
from src.infrastructure.database.client import db_client

logger = logging.getLogger(__name__)

class UserRepository:
    async def get_user(self, user_id: int):
        conn = db_client.get_connection()
        async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

    async def create_or_update_user(self, user_id: int, username: str, display_name: str):
        conn = db_client.get_connection()
        # Verificar si el usuario ya existe
        user = await self.get_user(user_id)
        
        is_admin = user_id in settings.ADMIN_USER_IDS

        if user:
            # Actualizar last_seen y display_name. Si está en ADMIN_USER_IDS, asegurar rol 'admin'.
            if is_admin and user['role'] != 'admin':
                await conn.execute(
                    "UPDATE users SET last_seen = CURRENT_TIMESTAMP, display_name = ?, role = 'admin' WHERE user_id = ?",
                    (display_name, user_id)
                )
            else:
                await conn.execute(
                    "UPDATE users SET last_seen = CURRENT_TIMESTAMP, display_name = ? WHERE user_id = ?",
                    (display_name, user_id)
                )
        else:
            # Crear nuevo usuario con rol estándar ('admin', 'vip', 'user')
            role = 'admin' if is_admin else 'user'
            relationship = 'none'
                
            await conn.execute(
                "INSERT INTO users (user_id, username, display_name, role, relationship) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, display_name, role, relationship)
            )
            logger.info(f"Nuevo usuario registrado: {username} ({user_id}) con rol: {role}")
        
        await conn.commit()
        return await self.get_user(user_id)

    async def set_role(self, user_id: int, role: str):
        """Asigna un rol estándar a un usuario ('admin', 'vip', 'user')."""
        if role not in ('admin', 'vip', 'user'):
            role = 'user'
        conn = db_client.get_connection()
        await conn.execute(
            "UPDATE users SET role = ? WHERE user_id = ?",
            (role, user_id)
        )
        await conn.commit()

    async def get_user_context(self, user_id: int) -> str:
        """Genera un string de contexto sobre el usuario para la IA."""
        user = await self.get_user(user_id)
        if not user:
            return "Usuario no registrado previamente."
        
        role = user['role'] if 'role' in user.keys() else 'user'
        context = f"Usuario: {user['display_name']} (Rol: {role})."
        
        if role == 'admin' or user_id in settings.ADMIN_USER_IDS:
            context += " [INFORMACIÓN]: Usuario con privilegios de Administrador del bot."
        elif role == 'vip':
            context += " [INFORMACIÓN]: Usuario con rol VIP del servidor."
        
        return context

    async def find_users_by_name(self, query: str):
        """Busca usuarios por nombre (username o display_name) para menciones sin tag."""
        conn = db_client.get_connection()
        search_query = f"%{query}%"
        async with conn.execute(
            "SELECT * FROM users WHERE username LIKE ? OR display_name LIKE ?", 
            (search_query, search_query)
        ) as cursor:
            return await cursor.fetchall()
