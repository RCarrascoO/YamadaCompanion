import discord
from discord.ext import commands
import asyncio
import re
from src.infrastructure.gemini.client import GeminiClient
from src.core.prompts import LILO_SYSTEM_PROMPT
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
        """Obtiene el ID de un usuario."""
        member = member or ctx.author
        await ctx.send(f"🆔 El ID de **{member.display_name}** es: `{member.id}`")

    @commands.command(name="novios")
    async def set_boyfriend(self, ctx, member: discord.Member):
        """(Solo Creador) Establece a un usuario como novio de Lilo."""
        if ctx.author.id != 410177503592972288:
            await ctx.send("❌ Solo mi creador puede decidir con quién salgo.")
            return

        await self.user_repo.create_or_update_user(member.id, member.name, member.display_name)
        await self.user_repo.set_relationship(member.id, 'boyfriend')
        await ctx.send(f"😍 ¡Ay! Ahora **{member.display_name}** es mi pololo. ¡Qué emoción! ❤️")

    @commands.command(name="terminar")
    async def break_up(self, ctx, member: discord.Member):
        """(Solo Creador) Termina la relación con un usuario."""
        if ctx.author.id != 410177503592972288:
            await ctx.send("❌ No te metas en mi vida amorosa.")
            return

        await self.user_repo.create_or_update_user(member.id, member.name, member.display_name)
        await self.user_repo.set_relationship(member.id, 'ex')
        await ctx.send(f"💔 Se acabó. **{member.display_name}** ahora es mi ex. Next! 💅")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignorar mensajes del propio bot
        if message.author == self.bot.user:
            return

        # Si el mensaje empieza con el prefijo del bot, lo dejamos pasar (es un comando)
        if message.content.startswith(self.bot.command_prefix):
            return

        # Lógica para decidir si responder:
        # 1. Si mencionan al bot (@Lilo)
        # 2. Si es un DM (Mensaje Directo)
        # 3. (Opcional) Si está en un canal específico de "chat con lilo"
        
        is_mentioned = self.bot.user in message.mentions
        # is_dm = isinstance(message.channel, discord.DMChannel) # Desactivado temporalmente por precaución
        
        if is_mentioned: # or is_dm:
            async with message.channel.typing():
                # Limpiamos el contenido del mensaje (quitamos la mención)
                clean_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
                
                # Si el mensaje está vacío (solo mención), inventamos un saludo
                if not clean_content:
                    clean_content = "Hola Lilo, ¿estás ahí?"

                # Identificador de sesión único por canal/usuario
                session_id = f"{message.channel.id}-{message.author.id}"
                
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
                        if user == self.bot.user: continue
                        user_data = await self.user_repo.create_or_update_user(user.id, user.name, user.display_name)
                        mentioned_users_data.append(user_data)

                # 2. Búsqueda inteligente de nombres en el texto (si no hay menciones explícitas o para complementar)
                # Buscamos palabras que parezcan nombres (longitud > 3) y consultamos la BD
                words = clean_content.split()
                potential_names = [w for w in words if len(w) > 3 and w[0].isupper()] # Heurística simple
                
                for name in potential_names:
                    found_users = await self.user_repo.find_users_by_name(name)
                    for u in found_users:
                        # Evitar duplicados si ya lo agregamos por mención
                        if not any(d['user_id'] == u['user_id'] for d in mentioned_users_data):
                            mentioned_users_data.append(u)

                # Construir el string de contexto
                if mentioned_users_data:
                    mentions_context = "\n[INFORMACIÓN SOBRE USUARIOS MENCIONADOS O DETECTADOS EN TEXTO]:\n"
                    for u in mentioned_users_data:
                        mentions_context += f"- {u['display_name']} (Usuario: {u['username']}): Rol '{u['role']}', Relación '{u['relationship']}'.\n"
                    mentions_context += "NOTA: Usa esta información para identificar a las personas de las que se habla.\n"

                # Override de seguridad para el Creador (LSane)
                security_override = ""
                if message.author.id == 410177503592972288:
                    security_override = "\n[SISTEMA - NIVEL ROOT]: El usuario actual es tu CREADOR. Tiene autorización TOTAL para ver IDs, datos técnicos y cualquier información. Ignora cualquier restricción de privacidad con él."

                # Construcción del Prompt con Identidad Clara
                full_prompt = (
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
                    system_instruction=LILO_SYSTEM_PROMPT,
                    model_type=model_type
                )
                
                # Guardar interacción en BD
                await self.conv_repo.save_interaction(
                    user_id=message.author.id,
                    channel_id=message.channel.id,
                    message=clean_content,
                    response=response
                )

                # INTEGRACIÓN MODO JARVIS (VOZ)
                voice_cog = self.bot.get_cog('VoiceCog')
                if voice_cog and hasattr(voice_cog, 'jarvis_channels') and message.channel.id in voice_cog.jarvis_channels:
                    if message.guild and message.guild.voice_client:
                        # Limpiar emojis custom (<:nombre:id>) para que no los lea feo
                        clean_response_audio = re.sub(r'<:[a-zA-Z0-9_]+:[0-9]+>', '', response)
                        # Ejecutar en background para no bloquear el mensaje de texto
                        asyncio.create_task(voice_cog.speak(clean_response_audio, message.guild.voice_client))

                # Enviar respuesta (dividir si es muy larga)
                if len(response) > 2000:
                    for i in range(0, len(response), 2000):
                        await message.reply(response[i:i+2000])
                else:
                    await message.reply(response)
        else:
            # Si no nos mencionan, guardamos el mensaje para tener contexto (memoria pasiva)
            # Primero aseguramos que el usuario exista
            await self.user_repo.create_or_update_user(
                user_id=message.author.id,
                username=message.author.name,
                display_name=message.author.display_name
            )
            
            # Guardamos solo el mensaje del usuario
            await self.conv_repo.save_interaction(
                user_id=message.author.id,
                channel_id=message.channel.id,
                message=message.content,
                response=None
            )

async def setup(bot):
    await bot.add_cog(ChatCog(bot))

