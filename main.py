from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import os

app = Flask(__name__)

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-pro")

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def get_page_content(page_id):
    url = f"{NOTION_API_URL}/blocks/{page_id}/children"
    response = requests.get(url, headers=NOTION_HEADERS)
    if response.status_code == 200:
        data = response.json()
        texts = []
        for block in data.get("results", []):
            if "paragraph" in block:
                texts.append("".join([r["text"]["content"] for r in block["paragraph"]["rich_text"]]))
        return "\n".join(texts)
    return None

def append_to_page(page_id, content):
    url = f"{NOTION_API_URL}/blocks/{page_id}/children"
    payload = {
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}],
                },
            }
        ]
    }
    requests.patch(url, headers=NOTION_HEADERS, json=payload)

@app.route("/notion", methods=["POST"])
def notion_webhook():
    data = request.json
    page_id = data.get("page_id")
    command = data.get("command", "")

    if not page_id or not command:
        return jsonify({"error": "page_id and command required"}), 400

    page_text = get_page_content(page_id)

    if command.startswith("\\traduzir"):
        prompt = f"Traduza o texto abaixo para português:\n\n{page_text}"
    elif command.startswith("\\resumir"):
        prompt = f"Resuma o seguinte texto:\n\n{page_text}"
    elif command.startswith("\\reescrever"):
        prompt = f"Reescreva de forma clara e organizada:\n\n{page_text}"
    elif command.startswith("\\conversar"):
        prompt = command.replace("\\conversar", "").strip()
        if not prompt:
            prompt = f"Converse sobre o seguinte texto:\n\n{page_text}"
    else:
        prompt = f"Você é uma IA ajudando no Notion. Execute o seguinte pedido:\n\n{command}\n\nTexto base:\n{page_text}"

    response = model.generate_content(prompt)
    ai_reply = response.text

    append_to_page(page_id, ai_reply)

    return jsonify({"reply": ai_reply})

@app.route("/")
def home():
    return "✅ Notion + Gemini rodando no Render!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
