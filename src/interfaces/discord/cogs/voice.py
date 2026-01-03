import discord
from discord.ext import commands
import wavelink
import edge_tts
import os
import logging
import asyncio

logger = logging.getLogger(__name__)

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Voz chilena de Edge TTS
        self.voice = "es-MX-DaliaNeural" 
        self.output_file = "/shared/tts_output.mp3"
        self.jarvis_channels = set() # Canales de texto donde Jarvis está activo

    async def generate_tts(self, text):
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(self.output_file)
        return self.output_file

    @commands.command(name="jarvis")
    async def toggle_jarvis(self, ctx):
        """Activa o desactiva el modo Jarvis (Respuestas por voz)."""
        if ctx.channel.id in self.jarvis_channels:
            self.jarvis_channels.remove(ctx.channel.id)
            await ctx.send("🔇 Modo Jarvis DESACTIVADO. Volveré a escribir en silencio.")
        else:
            if not ctx.author.voice:
                return await ctx.send("⚠️ Debes estar en un canal de voz para activar el modo Jarvis.")
            
            # Conectar si es necesario
            if not ctx.voice_client:
                try:
                    await ctx.author.voice.channel.connect(cls=wavelink.Player)
                except Exception as e:
                    return await ctx.send(f"Error al conectar: {e}")
            
            self.jarvis_channels.add(ctx.channel.id)
            await ctx.send("🎙️ **Modo Jarvis ACTIVADO**. Ahora leeré mis respuestas en voz alta.")
            await self.speak("Sistemas de voz en línea. Modo Jarvis activado.", ctx.voice_client)

    async def speak(self, text: str, player: wavelink.Player):
        """Lee un texto en el canal de voz, gestionando la música de fondo."""
        if not player or not player.channel:
            return

        try:
            # Generar audio
            await self.generate_tts(text)
            
            # Buscar track local
            tracks = await wavelink.Playable.search(self.output_file, source=None)
            if not tracks:
                logger.error("No se pudo cargar el archivo TTS.")
                return

            tts_track = tracks[0]
            
            # Guardar estado actual
            was_playing = player.playing
            previous_track = player.current
            previous_position = player.position
            
            # Marcar que estamos hablando (para evitar embeds de música si los hubiera)
            player.speaking = True
            
            # Reproducir TTS
            await player.play(tts_track)
            
            # Esperar a que termine (duración + buffer)
            if tts_track.length:
                await asyncio.sleep(tts_track.length / 1000 + 0.5)
            else:
                await asyncio.sleep(5) 
            
            # Restaurar música si estaba sonando
            if was_playing and previous_track:
                # Wavelink 3.x: play reemplaza el track actual.
                # Si queremos resumir, volvemos a tocar el anterior desde la posición
                await player.play(previous_track, start=previous_position)
            
            player.speaking = False
                
        except Exception as e:
            logger.error(f"Error en speak: {e}")
            player.speaking = False

    @commands.command(name="cambiarvoz", aliases=["setvoice"])
    async def change_voice_command(self, ctx, voice_code: str):
        """Cambia la voz de Lilo. Ejemplo: !cambiarvoz es-MX-DaliaNeural"""
        self.voice = voice_code
        await ctx.send(f"🗣️ Voz cambiada a: `{self.voice}`. ¡Pruébame con !say!")

    @commands.command(name="say", aliases=["habla"])
    async def say_command(self, ctx, *, text: str):
        """Hace que Lilo diga algo en el canal de voz."""
        if not ctx.author.voice:
            return await ctx.send("Debes estar en un canal de voz para escucharme.")

        destination = ctx.author.voice.channel
        
        # Conectar si no está conectada
        if not ctx.voice_client:
            player = await destination.connect(cls=wavelink.Player)
        else:
            player = ctx.voice_client
            if player.channel != destination:
                await player.move_to(destination)

        # Usar el método centralizado speak
        await ctx.typing()
        await self.speak(text, player)

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
