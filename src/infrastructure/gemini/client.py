import google.generativeai as genai
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        # Modelo por defecto (Gemma 3 - Alto límite)
        self.default_model = genai.GenerativeModel('gemma-3-27b-it')
        # Modelo para Jarvis 2 (Gemini 3 Flash Preview - Multimodal Audio Input)
        # Corregido: El nombre exacto en la API es 'gemini-3-flash-preview'
        self.flash_model = genai.GenerativeModel('gemini-3-flash-preview')
        
        self.chat_sessions = {}  # Diccionario simple para guardar sesiones por usuario/canal

    async def generate_response(self, prompt: str, history: list = None, system_instruction: str = None, model_type: str = "default", audio_data: bytes = None) -> str:
        try:
            # Seleccionar modelo
            model = self.flash_model if model_type == "flash" else self.default_model

            # Configuración de generación
            generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                temperature=0.9,
            )

            content = []
            
            # Si hay instrucción de sistema, la añadimos como texto
            if system_instruction:
                content.append(system_instruction)
            
            # Si hay audio, lo añadimos
            if audio_data:
                content.append({
                    "mime_type": "audio/wav",
                    "data": audio_data
                })
                # Si hay prompt de texto junto con audio, lo añadimos también
                if prompt:
                    content.append(f"User context: {prompt}")
            else:
                # Solo texto
                if system_instruction:
                    content = f"{system_instruction}\n\nUser: {prompt}"
                else:
                    content = prompt

            response = await model.generate_content_async(
                content,
                generation_config=generation_config
            )
            
            return response.text
        except Exception as e:
            logger.error(f"Error generando respuesta con Gemini ({model_type}): {e}")
            if "429" in str(e) or "Resource has been exhausted" in str(e):
                return "¡Espera un poco! Mucha gente hablándome a la vez... dame unos segundos para respirar. 😮‍💨"
            return "¡Chuta! Me mareé un poco... (Error de conexión con mi cerebro 😵‍💫)"

    def get_chat_session(self, session_id: str, system_instruction: str = None):
        """
        Obtiene o crea una sesión de chat persistente.
        """
        if session_id not in self.chat_sessions:
            # Al crear el chat, podemos pasarle la 'history' inicial con la personalidad
            history = []
            if system_instruction:
                history.append({"role": "user", "parts": [f"Instrucción de sistema: {system_instruction}"]})
                history.append({"role": "model", "parts": ["¡Entendido! Actuaré según esa personalidad."]})
            
            self.chat_sessions[session_id] = self.model.start_chat(history=history)
        
        return self.chat_sessions[session_id]

    async def send_message_async(self, session_id: str, message: str) -> str:
        """
        Envía un mensaje a una sesión específica manteniendo el contexto.
        """
        try:
            chat = self.get_chat_session(session_id)
            response = await chat.send_message_async(message)
            return response.text
        except Exception as e:
            logger.error(f"Error en chat {session_id}: {e}")
            return "Ups, se me fue la onda... ¿Qué decías? 😅"
