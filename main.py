import os
import json
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Cargar catálogo de productos
with open("productos.json", "r", encoding="utf-8") as f:
    productos = json.load(f)

# Cargar conocimiento del proyecto
with open("conocimiento.txt", "r", encoding="utf-8") as f:
    conocimiento = f.read()
# Cliente Anthropic
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class Pregunta(BaseModel):
    mensaje: str

@app.post("/chat")
async def chat(pregunta: Pregunta):
    catalogo_texto = json.dumps(productos, ensure_ascii=False, indent=2)

    system_prompt = f"""
{conocimiento}

Catálogo de productos disponible:
{catalogo_texto}

IMPORTANTE: Cuando menciones un producto específico termina con:
PRODUCTO_ID: el-id-del-producto
"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": pregunta.mensaje}]
    )

    texto_completo = response.content[0].text
    imagen_url = None
    producto_encontrado = None

    # Detectar qué producto mencionó Claude
    lineas = texto_completo.split("\n")
    texto_limpio = []

    for linea in lineas:
        if linea.strip().startswith("PRODUCTO_ID:"):
            producto_id = linea.split(":", 1)[1].strip()
            producto_encontrado = next(
                (p for p in productos if p["id"] == producto_id), None
            )
            if producto_encontrado:
                imagen_url = producto_encontrado.get("imagen")
        else:
            texto_limpio.append(linea)

    return {
        "respuesta": "\n".join(texto_limpio).strip(),
        "imagen": imagen_url,
        "producto": producto_encontrado
    }

# Servir archivos estáticos (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")
