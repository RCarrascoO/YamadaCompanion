import discord
from discord.ext import commands
import asyncio
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from src.core.config import settings
from src.infrastructure.gemini.client import GeminiClient
from src.core.prompts import YAMADA_DISCORD_PROMPT
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.repositories.conversation_repository import ConversationRepository
import logging

logger = logging.getLogger(__name__)

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gemini = GeminiClient()
        self.user_repo = UserRepository()
        self.conv_repo = ConversationRepository()

    @commands.command(name="id")
    async def get_user_id(self, ctx, member: discord.Member = None):
        """Obtiene el ID de Discord de un usuario o del autor del mensaje."""
        member = member or ctx.author
        await ctx.send(f"🆔 El ID de **{member.display_name}** es: `{member.id}`")

    @commands.command(name="info")
    async def info_command(self, ctx):
        """Muestra la información técnica, capacidades y estado de Yamada."""
        async with ctx.typing():
            prompt = (
                "El usuario ejecutó el comando !info. "
                "Preséntate como Yamada Companion. "
                "Explica de forma clara, amigable y estructurada tus características técnicas principales: "
                "1. Chat inteligente multicontexto con IA (Gemini / Gemma). "
                "2. Reproductor multimedia de alta fidelidad con Lavalink v4 y Wavelink. "
                "3. Síntesis y reconocimiento de voz interactivo con Edge TTS. "
                "4. Memoria contextual asíncrona respaldada por SQLite. "
                "Usa formato markdown limpio, viñetas y emojis geek. Mantén un tono servicial y profesional."
            )
            response = await self.gemini.generate_response(prompt, system_instruction=YAMADA_DISCORD_PROMPT)
            await ctx.send(response)

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignorar mensajes del propio bot
        if message.author == self.bot.user:
            return

        # Si el mensaje empieza con el prefijo del bot, lo dejamos pasar (es un comando)
        if message.content.startswith(self.bot.command_prefix):
            return

        # Lógica para decidir si responder: mención directa al bot
        is_mentioned = self.bot.user in message.mentions
        
        if is_mentioned:
            async with message.channel.typing():
                # Limpiamos el contenido del mensaje (quitamos la mención)
                clean_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
                
                # Si el mensaje está vacío (solo mención), saludo por defecto
                if not clean_content:
                    clean_content = "Hola Yamada, ¿estás ahí?"

                # Actualizar información del usuario en BD
                await self.user_repo.create_or_update_user(
                    user_id=message.author.id,
                    username=message.author.name,
                    display_name=message.author.display_name
                )
                
                # Obtener contexto del usuario desde BD
                user_context = await self.user_repo.get_user_context(message.author.id)
                
                # Obtener historial de conversación reciente
                chat_history = await self.conv_repo.get_recent_context(message.channel.id)
                
                # Contexto de Usuarios Mencionados (Anti-Alucinación)
                mentions_context = ""
                mentioned_users_data = []

                # 1. Menciones explícitas (@Usuario)
                if message.mentions:
                    for user in message.mentions:
                        if user == self.bot.user:
                            continue
                        user_data = await self.user_repo.create_or_update_user(user.id, user.name, user.display_name)
                        mentioned_users_data.append(user_data)

                # 2. Búsqueda contextual de nombres en el texto
                words = clean_content.split()
                potential_names = [w for w in words if len(w) > 3 and w[0].isupper()]
                
                for name in potential_names:
                    found_users = await self.user_repo.find_users_by_name(name)
                    for u in found_users:
                        if not any(d['user_id'] == u['user_id'] for d in mentioned_users_data):
                            mentioned_users_data.append(u)

                # Construir el string de contexto
                if mentioned_users_data:
                    mentions_context = "\n[INFORMACIÓN SOBRE USUARIOS MENCIONADOS EN EL TEXTO]:\n"
                    for u in mentioned_users_data:
                        role = u['role'] if 'role' in u.keys() else 'user'
                        mentions_context += f"- {u['display_name']} (Usuario: {u['username']}): Rol '{role}'.\n"
                    mentions_context += "NOTA: Usa esta información para identificar adecuadamente a las personas mencionadas.\n"

                # Override de permisos para Administradores
                security_override = ""
                if message.author.id in settings.ADMIN_USER_IDS:
                    security_override = "\n[SISTEMA - PRIVILEGIOS DE ADMINISTRADOR]: El usuario actual es Administrador del bot. Posee autorización para consultar configuraciones técnicas y diagnósticos del sistema."

                # Obtener Fecha y Hora
                try:
                    chile_tz = ZoneInfo("America/Santiago")
                    now = datetime.now(chile_tz)
                except Exception:
                    now = datetime.now()
                
                time_context = f"[SISTEMA - FECHA/HORA ACTUAL]: {now.strftime('%Y-%m-%d %H:%M:%S')}"

                # Construcción del Prompt con Identidad Clara
                full_prompt = (
                    f"{time_context}\n"
                    f"{user_context}\n"
                    f"{security_override}\n"
                    f"{chat_history}\n"
                    f"{mentions_context}\n"
                    f"[MENSAJE ACTUAL]\n"
                    f"Usuario: {message.author.display_name} (ID: {message.author.id})\n"
                    f"Dice: {clean_content}"
                )

                # Determinar modelo a usar (Default vs Flash/Jarvis2)
                model_type = "default"
                voice_cog = self.bot.get_cog('VoiceCog')
                if voice_cog and hasattr(voice_cog, 'jarvis2_channels') and message.channel.id in voice_cog.jarvis2_channels:
                    model_type = "flash"

                # Generar respuesta
                response = await self.gemini.generate_response(
                    prompt=full_prompt,
                    system_instruction=YAMADA_DISCORD_PROMPT,
                    model_type=model_type
                )
                
                # Guardar interacción en BD
                await self.conv_repo.save_interaction(
                    user_id=message.author.id,
                    channel_id=message.channel.id,
                    message=clean_content,
                    response=response
                )

                # Integración con modo voz / Jarvis si está activo en el canal
                if voice_cog and hasattr(voice_cog, 'jarvis_channels') and message.channel.id in voice_cog.jarvis_channels:
                    if message.guild and message.guild.voice_client:
                        clean_response_audio = re.sub(r'<:[a-zA-Z0-9_]+:[0-9]+>', '', response)
                        asyncio.create_task(voice_cog.speak(clean_response_audio, message.guild.voice_client))

                # Enviar respuesta respetando límite de caracteres de Discord
                if len(response) > 2000:
                    for i in range(0, len(response), 2000):
                        await message.reply(response[i:i+2000])
                else:
                    await message.reply(response)
        else:
            # Memoria pasiva: registrar mensajes en el canal para contexto
            await self.user_repo.create_or_update_user(
                user_id=message.author.id,
                username=message.author.name,
                display_name=message.author.display_name
            )
            
            await self.conv_repo.save_interaction(
                user_id=message.author.id,
                channel_id=message.channel.id,
                message=message.content,
                response=None
            )

async def setup(bot):
    await bot.add_cog(ChatCog(bot))
