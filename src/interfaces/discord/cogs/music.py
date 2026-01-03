import discord
from discord.ext import commands
import wavelink
import edge_tts
import asyncio
import random
from src.core.config import settings
from src.interfaces.discord.views.player_controls import PlayerControls
from src.infrastructure.gemini.client import GeminiClient
import logging

logger = logging.getLogger(__name__)

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.nodes = None
        self.gemini = GeminiClient()

    async def setup_hook(self):
        # Configuración del nodo de Lavalink
        # IMPORTANTE: Usamos el host configurado en .env (que ahora es 'lavalink' para docker)
        node = wavelink.Node(
            uri=f"http://{settings.LAVALINK_HOST}:{settings.LAVALINK_PORT}",
            password=settings.LAVALINK_PASSWORD
        )
        # Conectamos el nodo
        # En wavelink 3.x, connect es una corrutina y se recomienda hacerlo en on_ready o similar
        # pero setup_hook se ejecuta antes de que el bot esté listo del todo.
        # Moveremos la conexión a un listener on_ready para asegurar que el loop esté listo.
        pass

    @commands.Cog.listener()
    async def on_ready(self):
        # Evitar reconectar si ya hay nodos
        if wavelink.Pool.nodes:
            return

        nodes = [
            wavelink.Node(
                uri=f"http://{settings.LAVALINK_HOST}:{settings.LAVALINK_PORT}",
                password=settings.LAVALINK_PASSWORD
            )
        ]
        try:
            await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)
            logger.info("Conectando a Lavalink...")
        except Exception as e:
            logger.error(f"Error conectando a Lavalink: {e}")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        logger.info(f"Wavelink Node conectado: {payload.node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player = payload.player
        if not player:
            return
        
        # Si el bot está hablando (TTS), no mostramos el embed de música
        if getattr(player, "speaking", False):
            return

        track = payload.track
        
        # Evitar loops si es un track de TTS
        if "tts_" in track.uri:
            return
        
        embed = discord.Embed(
            title="🎶 Reproduciendo Ahora", 
            description=f"**{track.title}**\nPor: {track.author}", 
            color=discord.Color.from_rgb(255, 0, 255)
        )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        
        if hasattr(player, "home"):
            view = PlayerControls(player, None)
            await player.home.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player:
            return
            
        # Ignorar si estamos hablando (TTS) o si el track terminó porque fue reemplazado
        # Convertimos reason a string por si es un Enum
        if getattr(player, "speaking", False) or str(payload.reason) == "REPLACED":
            return

        # Reproducir siguiente canción si hay en la cola
        if not player.queue.is_empty:
            await player.play(player.queue.get())
        # Si la cola está vacía, podríamos desconectar o avisar, pero por ahora lo dejamos así.

    @commands.command(name="join", aliases=["j"])
    async def join_command(self, ctx):
        """Invita a Lilo al canal de voz."""
        if not ctx.author.voice:
            return await ctx.send("No estás en un canal de voz. ¿Dónde quieres que entre? 🤨")
        
        destination = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(destination)
            player = ctx.voice_client
        else:
            player = await destination.connect(cls=wavelink.Player)
        
        # Guardamos el canal de texto para enviar mensajes luego
        player.home = ctx.channel
        await ctx.send(f"Conectada a **{destination.name}**. ¡Lista para el show! 🎧")

        # Saludo de bienvenida
        try:
            frases_bienvenida = [
                "¡Hola a todos! ¿Cómo están? Lista para poner buena música.",
                "¡Llegó Lilo! Espero que estén teniendo un gran día.",
                "¡Buenas buenas! ¿Qué vamos a escuchar hoy?",
                "¡Hola! Ya estoy aquí. Pídanme lo que quieran.",
                "¡Wena los cabros! ¿Listos para el mambo?",
                "¡Hola! Me encanta que me inviten. ¿Cómo va todo?",
                "¡Llegué! Y traje mis mejores playlists."
            ]
            saludo = random.choice(frases_bienvenida)
            
            # Obtener voz actual
            voice_cog = self.bot.get_cog('VoiceCog')
            voice = voice_cog.voice if voice_cog else "es-CL-CatalinaNeural"
            
            # Generar TTS
            tts_path = "/shared/tts_welcome.mp3"
            communicate = edge_tts.Communicate(saludo, voice)
            await communicate.save(tts_path)
            
            # Reproducir TTS
            player.speaking = True
            tts_tracks = await wavelink.Playable.search(tts_path, source=None)
            if tts_tracks:
                tts_track = tts_tracks[0]
                await player.play(tts_track)
                # No necesitamos esperar aquí porque no hay canción que reanudar
                # Solo marcamos speaking=False después de un tiempo prudente o dejamos que el evento track_end lo maneje
                # Pero como track_end ignora si speaking=True, mejor lo manejamos aquí simple
                if tts_track.length:
                    await asyncio.sleep(tts_track.length / 1000)
                else:
                    await asyncio.sleep(3)
            player.speaking = False
            
        except Exception as e:
            logger.error(f"Error en saludo de bienvenida: {e}")
            if player:
                player.speaking = False

    @commands.command(name="play", aliases=["p"])
    async def play_command(self, ctx, *, search: str):
        """Reproduce una canción o playlist (YouTube/SoundCloud/Spotify)."""
        if not ctx.voice_client:
            await ctx.invoke(self.join_command)
            if not ctx.voice_client: # Si falló al unirse
                return

        player: wavelink.Player = ctx.voice_client
        # Asegurar que tenemos el canal de texto guardado
        if not hasattr(player, "home"):
            player.home = ctx.channel
        
        # Buscar la canción
        tracks = await wavelink.Playable.search(search)
        if not tracks:
            return await ctx.send("No encontré nada con ese nombre. ¿Seguro que existe? 🤔")

        if isinstance(tracks, wavelink.Playlist):
            # Es una playlist
            added = 0
            for track in tracks:
                await player.queue.put_wait(track)
                added += 1
            await ctx.send(f"✅ Añadida playlist **{tracks.name}** ({added} canciones) a la cola.")
        else:
            # Es una canción individual
            track = tracks[0]
            await player.queue.put_wait(track)
            await ctx.send(f"✅ Añadido a la cola: **{track.title}**")
        
        if not player.playing:
            await player.play(player.queue.get())
            # El mensaje con botones se envía en on_wavelink_track_start

    @commands.command(name="stop", aliases=["leave", "disconnect"])
    async def stop_command(self, ctx):
        """Detiene la música y desconecta a Lilo."""
        if not ctx.voice_client:
            return await ctx.send("Ni siquiera estoy conectada... 🙄")
        
        await ctx.voice_client.disconnect()
        await ctx.send("Desconectada. ¡Nos vemos! 👋")

    @commands.command(name="skip", aliases=["s"])
    async def skip_command(self, ctx):
        """Salta la canción actual."""
        if not ctx.voice_client or not ctx.voice_client.playing:
            return await ctx.send("No hay nada sonando para saltar.")
        
        # Si estamos en medio de una intro (speaking=True), forzamos el skip y limpiamos el estado
        if getattr(ctx.voice_client, "speaking", False):
            ctx.voice_client.speaking = False
            ctx.voice_client.just_spoke_fact = True # Para que no haga intro en la siguiente si saltamos rápido
        
        await ctx.voice_client.skip(force=True)
        await ctx.send("⏭️ Canción saltada.")

    @commands.command(name="pause")
    async def pause_command(self, ctx):
        """Pausa la reproducción."""
        if not ctx.voice_client or not ctx.voice_client.playing:
            return await ctx.send("No hay nada sonando.")
        await ctx.voice_client.pause(True)
        await ctx.send("⏸️ Pausado.")

    @commands.command(name="resume")
    async def resume_command(self, ctx):
        """Reanuda la reproducción."""
        if not ctx.voice_client or not ctx.voice_client.paused:
            return await ctx.send("No está pausado.")
        await ctx.voice_client.pause(False)
        await ctx.send("▶️ Reanudado.")

    @commands.command(name="queue", aliases=["q"])
    async def queue_command(self, ctx):
        """Muestra la cola de reproducción."""
        if not ctx.voice_client or ctx.voice_client.queue.is_empty:
            return await ctx.send("La cola está vacía.")
        
        embed = discord.Embed(title="Cola de Reproducción", color=discord.Color.blue())
        queue_list = list(ctx.voice_client.queue)
        desc = ""
        for i, track in enumerate(queue_list[:10], 1):
            desc += f"{i}. {track.title} - {track.author}\n"
        
        if len(queue_list) > 10:
            desc += f"... y {len(queue_list) - 10} más."
            
        embed.description = desc
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MusicCog(bot))
