import discord
from discord.ext import commands, voice_recv
import wavelink
import edge_tts
import os
import logging
import asyncio
from src.infrastructure.voice.sink import LiloAudioSink
from src.core.prompts import LILO_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Voz chilena de Edge TTS
        self.voice = "es-MX-DaliaNeural" 
        self.output_file = "/shared/tts_output.mp3"
        self.jarvis_channels = set() # Canales de texto donde Jarvis está activo
        self.jarvis2_channels = set() # Canales donde se usa Gemini 2.0 Flash
        self.listening_channels = {} # Canales donde estamos escuchando activamente

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

    @commands.command(name="jarvis2")
    async def toggle_jarvis2(self, ctx):
        """Activa el modo Jarvis 2.0 (Gemini 2.5 Flash + Voz Bidireccional)."""
        if ctx.channel.id in self.jarvis2_channels:
            self.jarvis2_channels.remove(ctx.channel.id)
            if ctx.channel.id in self.jarvis_channels:
                self.jarvis_channels.remove(ctx.channel.id)
            
            # Detener escucha si está activa
            if ctx.guild.id in self.listening_channels:
                if ctx.voice_client:
                    ctx.voice_client.stop_listening()
                del self.listening_channels[ctx.guild.id]

            await ctx.send("🔇 Modo Jarvis 2.0 DESACTIVADO. Volviendo a sistemas base.")
        else:
            if not ctx.author.voice:
                return await ctx.send("⚠️ Debes estar en un canal de voz para activar el modo Jarvis 2.0.")
            
            # Conectar si es necesario (Usando VoiceRecvClient para escuchar)
            if not ctx.voice_client:
                try:
                    # IMPORTANTE: Para escuchar, necesitamos VoiceRecvClient.
                    # Esto puede entrar en conflicto con Wavelink si se usa !play.
                    # Por ahora, priorizamos Jarvis 2.0.
                    await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
                except Exception as e:
                    return await ctx.send(f"Error al conectar: {e}")
            elif not isinstance(ctx.voice_client, voice_recv.VoiceRecvClient):
                # Si ya está conectado pero no es VoiceRecvClient (ej. Wavelink), avisamos
                await ctx.send("⚠️ Ya estoy conectada en modo Música. Para usar Jarvis 2.0 con escucha, necesito reconectarme. Desconéctame primero (`!disconnect`) o usa `!jarvis` normal.")
                return

            self.jarvis_channels.add(ctx.channel.id) # Activa voz salida
            self.jarvis2_channels.add(ctx.channel.id) # Activa cerebro Flash
            self.listening_channels[ctx.guild.id] = True

            # Iniciar escucha con callback para evitar eco
            # Definimos una función lambda que verifica si el cliente está reproduciendo audio
            is_speaking = lambda: ctx.voice_client.is_playing() if isinstance(ctx.voice_client, voice_recv.VoiceRecvClient) else False
            
            ctx.voice_client.listen(LiloAudioSink(self.process_audio, self.bot.loop, is_speaking_callback=is_speaking))
            
            await ctx.send("🚀 **MODO JARVIS 2.0 ACTIVADO**\nCerebro: Gemini 3 Flash Preview\nOído: Activado 👂\n¡Háblame!")
            # await self.speak("Sistemas auditivos en línea. Te escucho.", ctx.voice_client) # Speak usa wavelink, podría fallar si usamos VoiceRecvClient puro.
            # Fallback a TTS simple si speak falla por tipo de cliente
            try:
                await self.speak("Sistemas auditivos en línea. Te escucho.", ctx.voice_client)
            except:
                pass

    async def process_audio(self, user_id, audio_data):
        """Callback cuando se detecta voz de un usuario."""
        logger.info(f"Procesando audio de usuario {user_id} ({len(audio_data)} bytes)")
        
        # Buscar el canal de texto asociado (asumimos el primero donde esté activo Jarvis 2)
        # Esto es una simplificación. Idealmente mapearíamos voice_channel -> text_channel
        target_channel_id = None
        for cid in self.jarvis2_channels:
            channel = self.bot.get_channel(cid)
            if channel and channel.guild.get_member(user_id):
                target_channel_id = cid
                break
        
        if not target_channel_id:
            return

        channel = self.bot.get_channel(target_channel_id)
        user = channel.guild.get_member(user_id)
        
        # Obtener cliente Gemini del cog de Chat
        chat_cog = self.bot.get_cog('ChatCog')
        if not chat_cog:
            return

        # Enviar audio a Gemini
        try:
            # Usamos el contexto de usuario del repositorio
            user_context = await chat_cog.user_repo.get_user_context(user_id)
            
            response_text = await chat_cog.gemini.generate_response(
                prompt=None, # No hay texto, solo audio
                system_instruction=f"{LILO_SYSTEM_PROMPT}\nEstás respondiendo a un mensaje de audio de {user.display_name}.",
                model_type="flash",
                audio_data=audio_data
            )
            
            if response_text:
                await channel.send(f"🎤 **{user.display_name}** (Audio) -> Lilo: {response_text}")
                # Leer respuesta
                if channel.guild.voice_client:
                     await self.speak(response_text, channel.guild.voice_client)

        except Exception as e:
            logger.error(f"Error procesando audio: {e}")
            await channel.send(f"❌ Error procesando audio: {e}")

    async def speak(self, text: str, player):
        """Lee un texto en el canal de voz, gestionando la música de fondo."""
        if not player or not player.channel:
            return

        try:
            # Generar audio
            await self.generate_tts(text)
            
            # Obtener duración estimada
            duration = 5.0
            tts_track = None
            try:
                tracks = await wavelink.Playable.search(self.output_file, source=None)
                if tracks:
                    tts_track = tracks[0]
                    duration = tts_track.length / 1000 + 0.5
            except Exception as e:
                logger.warning(f"No se pudo obtener duración del audio: {e}")

            # CASO 1: Wavelink Player (Música + Jarvis 1)
            if isinstance(player, wavelink.Player):
                if not tts_track:
                    logger.error("No se pudo cargar el archivo TTS para Wavelink.")
                    return

                # Guardar estado actual
                was_playing = player.playing
                previous_track = player.current
                previous_position = player.position
                
                # Marcar que estamos hablando
                player.speaking = True
                
                # Reproducir TTS
                await player.play(tts_track)
                
                # Esperar a que termine
                await asyncio.sleep(duration)
                
                # Restaurar música si estaba sonando
                if was_playing and previous_track:
                    await player.play(previous_track, start=previous_position)
                
                player.speaking = False
            
            # CASO 2: VoiceRecvClient (Jarvis 2.0)
            elif isinstance(player, voice_recv.VoiceRecvClient):
                logger.info(f"Hablando en modo Jarvis 2.0 (Duración: {duration}s)")
                
                # 1. Detener escucha TEMPORALMENTE (Fix CryptoError/Stability)
                # Esto evita que el bot se escuche a sí mismo y previene desincronización del socket
                player.stop_listening()
                
                # 2. Reproducir audio
                if player.is_playing():
                    player.stop()

                source = discord.FFmpegPCMAudio(self.output_file)
                player.play(source)
                
                # 3. Esperar a que termine
                await asyncio.sleep(duration)
                
                # 4. Reiniciar escucha
                if player.is_connected():
                    logger.info("Reiniciando escucha tras hablar...")
                    is_speaking = lambda: player.is_playing()
                    player.listen(LiloAudioSink(self.process_audio, self.bot.loop, is_speaking_callback=is_speaking))
                
        except Exception as e:
            logger.error(f"Error en speak: {e}")

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
