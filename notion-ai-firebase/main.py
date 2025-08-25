import functions_framework
from flask import jsonify, request
from notion_client import Client
import google.generativeai as genai
import os

# As chaves ficam em variáveis de ambiente do Firebase
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

notion = Client(auth=NOTION_TOKEN)
genai.configure(api_key=GEMINI_KEY)

def processar_comando(page_id, block_id, conteudo, blocks):
    if conteudo.strip().startswith("\\resumir"):
        return executar_resumo(page_id, block_id, blocks)
    elif conteudo.strip().startswith("\\traduzir"):
        return executar_traducao(page_id, block_id, blocks, "en")
    elif conteudo.strip().startswith("\\reescrever"):
        return executar_reescrita(page_id, block_id, conteudo)
    return None

def executar_resumo(page_id, comando_block_id, blocks):
    texto = coletar_texto(blocks)
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(f"Resuma em português o seguinte texto:\n\n{texto}")
    adicionar_bloco(page_id, resp.text, "✨ Resumo")
    notion.blocks.delete(comando_block_id)

def executar_traducao(page_id, comando_block_id, blocks, idioma_destino="en"):
    texto = coletar_texto(blocks)
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(f"Traduza para {idioma_destino} o seguinte texto:\n\n{texto}")
    adicionar_bloco(page_id, resp.text, "🌎 Tradução")
    notion.blocks.delete(comando_block_id)

def executar_reescrita(page_id, comando_block_id, conteudo):
    original = conteudo.replace("\\reescrever", "").strip()
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(f"Reescreva de forma mais clara:\n\n{original}")
    adicionar_bloco(page_id, resp.text, "✍ Reescrita")
    notion.blocks.delete(comando_block_id)

def coletar_texto(blocks):
    texto = []
    for b in blocks:
        if b["type"] in ("paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item"):
            rich = b[b["type"]]["rich_text"]
            texto.append("".join([r["plain_text"] for r in rich]))
    return "\n".join(texto)

def adicionar_bloco(page_id, conteudo, titulo="💡 Resultado"):
    notion.blocks.children.append(
        page_id,
        children=[{
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"{titulo}\n\n{conteudo}"}}],
                "icon": {"emoji": "🤖"}
            }
        }]
    )

# 🔥 Entry point para Firebase
@functions_framework.http
def notion_webhook(request):
    data = request.get_json(silent=True) or {}

    try:
        page_id = data["payload"]["page"]["id"]
        block_id = data["payload"]["block"]["id"]
    except Exception:
        return jsonify({"status": "ignored"}), 200

    blocks = notion.blocks.children.list(page_id).get("results", [])

    for block in blocks:
        if block["type"] == "paragraph":
            text_items = block["paragraph"]["rich_text"]
            conteudo = "".join([t["plain_text"] for t in text_items])
            processar_comando(page_id, block["id"], conteudo, blocks)

    return jsonify({"status": "ok"}), 200
