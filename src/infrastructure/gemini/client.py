import google.generativeai as genai
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        # Usando gemma-3-27b-it para aprovechar el límite de 14.4K peticiones diarias (vs 20 de Gemini)
        self.model = genai.GenerativeModel('gemma-3-27b-it')
        self.chat_sessions = {}  # Diccionario simple para guardar sesiones por usuario/canal

    async def generate_response(self, prompt: str, history: list = None, system_instruction: str = None) -> str:
        try:
            # Configuración de generación para que sea más "creativa" (temperatura)
            generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                temperature=0.9, # Alto para que sea expresiva y divertida
            )

            # Si hay instrucción de sistema (personalidad), la inyectamos
            # Nota: En la API de Python, system_instruction se pasa al crear el modelo, 
            # pero para hacerlo dinámico por mensaje a veces es mejor inyectarlo en el prompt 
            # o mantener una sesión con historia.
            
            # Para simplificar y mantener contexto, usaremos chat sessions
            # Pero aquí haremos una llamada stateless simple si no hay historia
            
            full_prompt = prompt
            if system_instruction:
                # Inyectamos la personalidad al principio si es una llamada única
                full_prompt = f"{system_instruction}\n\nUser: {prompt}"

            response = await self.model.generate_content_async(
                full_prompt,
                generation_config=generation_config
            )
            
            return response.text
        except Exception as e:
            logger.error(f"Error generando respuesta con Gemini: {e}")
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
