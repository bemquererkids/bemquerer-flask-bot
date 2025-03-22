
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
import os
import csv
import openai
import pandas as pd
import time
import random

app = Flask(__name__)

# Lendo contexto fixo da clínica
with open('contexto.txt', 'r') as file:
    contexto_clinica = file.read()

# Configuração OpenAI usando variável de ambiente
openai.api_key = os.getenv("OPENAI_API_KEY")

csv_filename = "leads.csv"

# Carregando FAQ
faq_df = pd.read_csv("faq.csv")

def salvar_csv(numero, mensagem, resposta):
    file_exists = os.path.isfile(csv_filename)
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Numero', 'Mensagem Recebida', 'Resposta Enviada'])
        writer.writerow([numero, mensagem, resposta])

def verificar_faq(mensagem):
    for index, row in faq_df.iterrows():
        if row['Pergunta'].lower() in mensagem.lower():
            return row['Resposta']
    return None

def gerar_resposta_ia(pergunta):
    resposta = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": contexto_clinica},
            {"role": "user", "content": pergunta}
        ]
    )
    return resposta["choices"][0]["message"]["content"].strip()

@app.route("/", methods=['POST'])
def index():
    numero = request.form.get('From')
    mensagem = request.form.get('Body').strip()

    print(f"📥 Mensagem recebida de {numero}: {mensagem}")

    # Primeiro verifica no FAQ
    resposta_faq = verificar_faq(mensagem)
    
    if resposta_faq:
        resposta = resposta_faq
        print("✅ Resposta enviada pelo FAQ")
    else:
        # Senão, chama OpenAI
        resposta = gerar_resposta_ia(mensagem)
        print("🤖 Resposta gerada pela OpenAI")
    
    salvar_csv(numero, mensagem, resposta)

    # Delay humanizado
    delay = random.randint(2, 4)
    time.sleep(delay)

    resp = MessagingResponse()
    resp.message(resposta)

    print(f"✅ Resposta enviada para {numero}")

    response = Response(str(resp), mimetype='application/xml')
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
