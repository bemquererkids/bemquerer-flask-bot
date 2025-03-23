from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
import os
import csv
import openai
import pandas as pd
import time
import random
import difflib

app = Flask(__name__)

# Lendo contexto fixo da clínica
with open('contexto.txt', 'r') as file:
    contexto_clinica = file.read()

# Configuração OpenAI usando variável de ambiente
openai.api_key = os.getenv("OPENAI_API_KEY")

csv_filename = "leads.csv"

# Carregando FAQ
faq_df = pd.read_csv("faq.csv")

# Função para salvar os leads recebidos
def salvar_csv(numero, mensagem, resposta):
    file_exists = os.path.isfile(csv_filename)
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Numero', 'Mensagem Recebida', 'Resposta Enviada'])
        writer.writerow([numero, mensagem, resposta])

# Verificar pergunta no FAQ com margem de flexibilidade (difflib)
def verificar_faq(mensagem):
    mensagem = mensagem.lower().strip()
    melhor_similaridade = 0
    resposta_encontrada = None
    
    for index, row in faq_df.iterrows():
        pergunta_faq = row['Pergunta'].lower().strip()
        similaridade = difflib.SequenceMatcher(None, pergunta_faq, mensagem).ratio()
        
        if similaridade > 0.6 and similaridade > melhor_similaridade:
            melhor_similaridade = similaridade
            resposta_encontrada = row['Resposta']
    
    return resposta_encontrada

# Função para gerar resposta via OpenAI (ChatGPT)
def gerar_resposta_ia(pergunta):
    resposta = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": contexto_clinica},
            {"role": "user", "content": pergunta}
        ]
    )
    return resposta["choices"][0]["message"]["content"].strip()

# Rota principal para receber e responder mensagens do Twilio WhatsApp
@app.route("/", methods=['POST'])
def index():
    numero = request.form.get('From')
    mensagem = request.form.get('Body').strip()

    print(f"📥 Mensagem recebida de {numero}: {mensagem}")

    # Verificar primeiro no FAQ
    resposta_faq = verificar_faq(mensagem)
    
    if resposta_faq:
        resposta = resposta_faq
        print("✅ Resposta enviada pelo FAQ (Similaridade Alta)")
    else:
        # Caso não encontre, gerar via OpenAI
        resposta = gerar_resposta_ia(mensagem)
        print("🤖 Resposta gerada pela OpenAI")
    
    salvar_csv(numero, mensagem, resposta)

    # Delay humanizado para parecer natural
    delay = random.randint(2, 4)
    time.sleep(delay)

    # Envia a resposta via Twilio
    resp = MessagingResponse()
    resp.message(resposta)

    print(f"✅ Resposta enviada para {numero}")

    response = Response(str(resp), mimetype='application/xml')
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Porta padrão Render
    app.run(host="0.0.0.0", port=port, debug=True)
