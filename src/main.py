import asyncio
import logging
import os
import sys
from discord.ext import commands
import discord
from src.core.config import settings
from src.infrastructure.database.client import db_client

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("LiloBot")

class LiloBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        
        super().__init__(
            command_prefix=settings.DISCORD_PREFIX,
            intents=intents,
            help_command=None,
            description="Lilo - Asistente Virtual Chilena"
        )

    async def setup_hook(self):
        logger.info(f"Iniciando Lilo en entorno: {settings.ENVIRONMENT}")
        
        # Inicializar Base de Datos
        await db_client.connect()
        
        # Cargamos los cogs
        await self.load_extension("src.interfaces.discord.cogs.chat")
        await self.load_extension("src.interfaces.discord.cogs.music")
        await self.load_extension("src.interfaces.discord.cogs.voice")
        logger.info("Setup completado.")

    async def on_ready(self):
        logger.info(f'Conectada como {self.user} (ID: {self.user.id})')
        logger.info('------')
        # Quitamos el "Escuchando tus dramas" y ponemos algo más Jarvis/Friday
        activity = discord.Activity(type=discord.ActivityType.watching, name="sistemas operativos 🖥️")
        await self.change_presence(activity=activity)

async def main():
    bot = LiloBot()
    async with bot:
        await bot.start(settings.DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Manejar cierre limpio
        pass
