import discord
import wavelink

class PlayerControls(discord.ui.View):
    def __init__(self, player: wavelink.Player, ctx):
        super().__init__(timeout=None)
        self.player = player
        self.ctx = ctx

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def previous_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player:
             return await interaction.response.send_message("No hay reproductor activo.", ephemeral=True)
        
        history = self.player.queue.history
        if not history:
            return await interaction.response.send_message("No hay canciones en el historial.", ephemeral=True)
        
        # Obtener la última canción del historial
        track = history[len(history) - 1]
        
        # Reproducirla
        await self.player.play(track)
        await interaction.response.send_message(f"⏮️ Volviendo a: **{track.title}**", ephemeral=True)

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.blurple, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player:
             return await interaction.response.send_message("No hay reproductor activo.", ephemeral=True)

        if self.player.paused:
            await self.player.pause(False)
            await interaction.response.send_message("▶️ Reanudado", ephemeral=True)
        else:
            await self.player.pause(True)
            await interaction.response.send_message("⏸️ Pausado", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player or not self.player.playing:
             return await interaction.response.send_message("No hay nada sonando.", ephemeral=True)
        await self.player.skip(force=True)
        await interaction.response.send_message("⏭️ Saltado", ephemeral=True)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.gray, row=0)
    async def shuffle_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player or self.player.queue.is_empty:
            return await interaction.response.send_message("La cola está vacía.", ephemeral=True)
        
        self.player.queue.shuffle()
        await interaction.response.send_message("🔀 Cola mezclada.", ephemeral=True)

    @discord.ui.button(emoji="⏪", label="-10s", style=discord.ButtonStyle.gray, row=1)
    async def rewind_10s(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player or not self.player.playing:
            return await interaction.response.send_message("No hay nada sonando.", ephemeral=True)
        
        position = self.player.position
        new_position = max(0, position - 10000) # ms
        await self.player.seek(new_position)
        await interaction.response.send_message("⏪ Retrocedido 10s", ephemeral=True)

    @discord.ui.button(emoji="⏩", label="+10s", style=discord.ButtonStyle.gray, row=1)
    async def forward_10s(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player or not self.player.playing:
            return await interaction.response.send_message("No hay nada sonando.", ephemeral=True)
        
        position = self.player.position
        new_position = position + 10000 # ms
        await self.player.seek(new_position)
        await interaction.response.send_message("⏩ Adelantado 10s", ephemeral=True)

    @discord.ui.button(emoji="📜", label="Cola", style=discord.ButtonStyle.gray, row=1)
    async def queue_list(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player or self.player.queue.is_empty:
            return await interaction.response.send_message("La cola está vacía.", ephemeral=True)
        
        # Crear la vista con el selector
        view = QueueSelectView(self.player)
        await interaction.response.send_message("Selecciona una canción de la cola para reproducirla ahora:", view=view, ephemeral=True)

class QueueSelect(discord.ui.Select):
    def __init__(self, player: wavelink.Player):
        self.player = player
        options = []
        # Limitamos a 25 opciones (límite de Discord)
        # Convertimos la cola a lista para iterar
        queue_list = list(player.queue)
        for i, track in enumerate(queue_list[:25]):
            # Truncamos título y autor si son muy largos
            label = f"{i+1}. {track.title}"[:99]
            description = track.author[:99] if track.author else "Desconocido"
            # El valor será el índice en la cola
            options.append(discord.SelectOption(label=label, description=description, value=str(i)))

        super().__init__(placeholder="Selecciona una canción...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            index = int(self.values[0])
            queue = self.player.queue
            
            # Obtener la canción
            track = queue[index]
            
            # Moverla al principio de la cola para que sea la siguiente
            del queue[index]
            
            # Usamos put_at para insertar al principio (índice 0)
            queue.put_at(0, track)
            
            # Saltamos la canción actual. 
            # Esto disparará on_track_end, que tomará la canción que acabamos de poner al frente.
            await self.player.skip(force=True)
            
            await interaction.response.send_message(f"⏭️ Saltando a: **{track.title}**", ephemeral=True)
        except IndexError:
            await interaction.response.send_message("Esa canción ya no parece estar en la cola.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error al saltar: {e}", ephemeral=True)

class QueueSelectView(discord.ui.View):
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=60)
        self.add_item(QueueSelect(player))
