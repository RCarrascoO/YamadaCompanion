# YamadaCompanion 🤖✨
### AI Discord Companion & Multimedia Assistant

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3+-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-AI%20Studio-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com/)
[![Lavalink](https://img.shields.io/badge/Lavalink-v4.0-E10098?style=for-the-badge)](https://github.com/lavalink-devs/Lavalink)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

**YamadaCompanion** es un asistente virtual inteligente y bot multimedia avanzado para comunidades y servidores de Discord. Combina modelos de inteligencia artificial multimodal (**Google Gemini** y **Gemma**) con streaming de audio de alta fidelidad vía **Lavalink v4**, síntesis de voz natural en tiempo real (**Microsoft Edge TTS**) y memoria conversacional asíncrona sobre **SQLite**.

---

## 🌟 Características Principales

- **🧠 Asistente Conversacional Inteligente:**
  - Respuestas contextuales y dinámicas impulsadas por los modelos de Google Gemini.
  - Memoria conversacional por canal y contexto personalizado por usuario.
  - Detección de usuarios mencionados para evitar alucinaciones.
- **🎵 Reproductor Musical de Alta Fidelidad:**
  - Motor de audio robusto impulsado por Lavalink v4 y Wavelink 3.x.
  - Búsqueda en YouTube, SoundCloud y compatibilidad con listas de reproducción.
  - Interfaz interactiva de Discord (botones para Play/Pause, Skip, Shuffle, Queue).
- **🎙️ Módulo de Voz y Síntesis (TTS):**
  - Lectura de mensajes en canales de voz mediante Edge TTS (`!say`, `!cambiarvoz`).
  - Modo Jarvis interactivo para leer respuestas del bot en vivo en el canal de voz.
  - Modo experimental Jarvis 2.0 con audio bidireccional y recepción por micrófono.
- **🛡️ Sistema de Roles y Privilegios:**
  - Soporte para roles `admin`, `vip` y `user`.
  - Configuración flexible de múltiples administradores a través de variables de entorno (`ADMIN_USER_IDS`).
- **🐳 Despliegue Rápido con Docker Compose:**
  - Orquestación lista para producción con aislamiento del bot y el servidor Lavalink.

---

## 🏛️ Arquitectura del Sistema

```text
                     +---------------------------------------+
                     |            Discord Gateway            |
                     +-------------------+-------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |         Yamada Discord Client         |
                     +---+------------------+-------------+--+
                         |                  |             |
                         v                  v             v
             +---------------+     +---------------+  +----------------+
             | Chat Cog (AI) |     | Music Cog     |  | Voice Cog      |
             +-------+-------+     +-------+-------+  +-------+--------+
                     |                     |                  |
           +---------+-------+             |                  |
           |                 |             |                  |
           v                 v             v                  v
     +----------+     +------------+  +---------+     +---------------+
     | Gemini   |     | SQLite DB  |  | Lavalink|     | Edge TTS      |
     | API      |     | (aiosqlite)|  | Node    |     | (Voz Síntesis)|
     +----------+     +------------+  +---------+     +---------------+
```

---

## 📋 Requisitos Previos

- **Docker** y **Docker Compose** (recomendado para despliegue en servidor).
- Alternativamente, si ejecutas en entorno local:
  - **Python 3.11+**
  - **Java 17+** (requerido para ejecutar Lavalink de forma nativa si no se usa Docker)
  - **FFmpeg** y bibliotecas de Opus (`libopus-dev`)
- **Discord Bot Token** con los Intents correspondientes activados (*Message Content*, *Server Members*, *Voice States*).
- **Google AI Studio API Key** (Gemini).

---

## 🚀 Despliegue Rápido con Docker Compose

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/RCarrascoO/YamadaCompanion.git
   cd YamadaCompanion
   ```

2. **Configurar las variables de entorno:**
   Copia el archivo de plantilla `.env.example` y edita los valores con tus credenciales:
   ```bash
   cp .env.example .env
   nano .env
   ```

3. **Iniciar los servicios:**
   ```bash
   docker compose up -d --build
   ```

4. **Verificar los logs:**
   ```bash
   docker compose logs -f yamada-bot
   ```

Para detener la ejecución:
```bash
docker compose down
```

---

## ⚙️ Configuración (.env)

| Variable | Descripción | Valor por Defecto / Ejemplo |
| :--- | :--- | :--- |
| `DISCORD_TOKEN` | Token secreto de la aplicación en Discord Developer Portal | `tu_token_aqui` |
| `DISCORD_PREFIX` | Prefijo para los comandos de texto | `!` |
| `ADMIN_USER_IDS` | IDs de Discord de administradores autorizados (separados por coma) | `123456789,987654321` |
| `GOOGLE_API_KEY` | Clave de acceso a la API de Google Gemini | `tu_google_api_key` |
| `LAVALINK_HOST` | Host del servidor Lavalink (`lavalink` en Docker, `localhost` en local) | `lavalink` |
| `LAVALINK_PORT` | Puerto de conexión REST/WebSocket de Lavalink | `2333` |
| `LAVALINK_PASSWORD` | Contraseña configurada en Lavalink `application.yml` | `youshallnotpass` |
| `ENVIRONMENT` | Entorno de ejecución (`development` / `production`) | `production` |
| `DB_PATH` | Ruta absoluta o relativa de la base de datos SQLite | `/shared/yamada.db` |

---

## 🎮 Comandos Disponibles

### 💬 Asistente y General
- `@Yamada <mensaje>`: Conversa directamente con el bot mencionándolo.
- `!info`: Muestra información técnica detallada, arquitectura y estado del bot.
- `!id [@usuario]`: Muestra el ID numérico de Discord del usuario o del autor del mensaje.

### 🎵 Música y Multimedia
- `!play <título | URL>` (o `!p`): Reproduce una canción o agrega una lista a la cola.
- `!pause`: Pausa la reproducción de audio actual.
- `!resume`: Reanuda la reproducción pausada.
- `!skip` (o `!s`): Salta a la siguiente pista en la cola.
- `!queue` (o `!q`): Muestra la lista de pistas pendientes en reproducción.
- `!join` (o `!j`): Conecta al bot al canal de voz del usuario emisor.
- `!stop` (o `!leave`): Detiene la música y desconecta al bot del canal de voz.

### 🎙️ Voz y Síntesis (TTS)
- `!say <mensaje>` (o `!habla`): Sintetiza un texto en el canal de voz activo vía Edge TTS.
- `!cambiarvoz <código>`: Cambia la voz TTS utilizada (ej. `es-MX-DaliaNeural`, `es-ES-AlvaroNeural`).
- `!jarvis`: Activa o desactiva la lectura por voz de las respuestas generadas en el chat.
- `!jarvis2`: Modo multimodal interactivo con reconocimiento y respuesta de voz.

---

## 🛠️ Estructura del Código

```text
YamadaCompanion/
├── docker/
│   ├── application.yml        # Configuración del servidor Lavalink v4
│   ├── docker-compose.yml     # Orquestación interna de servicios
│   └── Dockerfile             # Imagen de contenedor Python optimizada
├── src/
│   ├── core/
│   │   ├── config.py          # Validación de entorno con Pydantic Settings
│   │   └── prompts.py         # System prompt y personalidad de Yamada
│   ├── infrastructure/
│   │   ├── database/          # Cliente aiosqlite y repositorios de datos
│   │   ├── gemini/            # Cliente e integración de Google Generative AI
│   │   └── voice/             # Sinks de audio PCM y procesamiento en tiempo real
│   ├── interfaces/
│   │   └── discord/
│   │       ├── cogs/          # Módulos de Discord (chat, music, voice)
│   │       └── views/         # Componentes UI (PlayerControls y botones)
│   └── main.py                # Punto de entrada de la aplicación
├── .env.example               # Plantilla segura de variables de entorno
├── docker-compose.yml         # Compose raíz para despliegue
├── requirements.txt           # Dependencias de Python
└── README.md                  # Documentación principal
```

---

## 🔒 Privacidad y Seguridad

YamadaCompanion fue diseñado para entornos abiertos y compartidos:
- No contiene credenciales ni datos personales hardcodeados.
- Toda la configuración confidencial se gestiona mediante variables de entorno seguras (`.env`).
- Los registros de bases de datos son locales a la instancia y no se comparten con terceros no autorizados.

---

## 📄 Licencia

Este proyecto se distribuye bajo los términos de la [Licencia MIT](LICENSE).
