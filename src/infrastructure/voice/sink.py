import time
import asyncio
import logging
import wave
import io
from discord.ext import voice_recv

logger = logging.getLogger(__name__)

class YamadaAudioSink(voice_recv.AudioSink):
    def __init__(self, callback, loop, is_speaking_callback=None):
        super().__init__()
        self.callback = callback
        self.loop = loop
        self.is_speaking_callback = is_speaking_callback
        self.user_buffers = {}
        self.user_last_packet = {}
        self.silence_threshold = 0.6  # Reducido a 0.6s para mayor rapidez
        self.processing_tasks = {}

    def wants_opus(self):
        return False  # Queremos PCM decodificado

    def write(self, user, data):
        if user is None:
            return
            
        # Si el bot está hablando, ignoramos el audio entrante (evitar eco)
        if self.is_speaking_callback and self.is_speaking_callback():
            return

        user_id = user.id
        
        if user_id not in self.user_buffers:
            logger.debug(f"Inicio de voz detectado para usuario {user_id}")
            self.user_buffers[user_id] = bytearray()
            self.user_last_packet[user_id] = time.time()
            # Iniciar monitor de silencio para este usuario
            self.processing_tasks[user_id] = self.loop.create_task(self.monitor_silence(user_id))

        self.user_buffers[user_id].extend(data.pcm)
        self.user_last_packet[user_id] = time.time()

    async def monitor_silence(self, user_id):
        while True:
            await asyncio.sleep(0.2)
            if user_id not in self.user_last_packet:
                break
                
            time_since_last = time.time() - self.user_last_packet[user_id]
            
            if time_since_last > self.silence_threshold:
                # Silencio detectado, procesar audio
                if user_id in self.user_buffers and len(self.user_buffers[user_id]) > 0:
                    audio_data = bytes(self.user_buffers[user_id])
                    # Limpiar buffer
                    del self.user_buffers[user_id]
                    del self.user_last_packet[user_id]
                    del self.processing_tasks[user_id]
                    
                    # Convertir PCM a WAV en memoria
                    wav_buffer = io.BytesIO()
                    with wave.open(wav_buffer, 'wb') as wav_file:
                        wav_file.setnchannels(2)     # Discord stereo
                        wav_file.setsampwidth(2)     # 16-bit
                        wav_file.setframerate(48000)  # 48kHz
                        wav_file.writeframes(audio_data)
                    
                    wav_buffer.seek(0)
                    
                    # Llamar al callback con el audio y el usuario
                    self.loop.create_task(self.callback(user_id, wav_buffer.read()))
                break

    def cleanup(self):
        self.user_buffers.clear()
        self.user_last_packet.clear()
        for task in self.processing_tasks.values():
            task.cancel()
