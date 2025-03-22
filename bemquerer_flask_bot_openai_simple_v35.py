from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
import os
import csv
import openai

app = Flask(__name__)

# Configuração OpenAI usando variável de ambiente
openai.api_key = os.getenv("OPENAI_API_KEY")

# Caminho do arquivo CSV (opcional para registro de mensagens)
csv_filename = "leads.csv"

# Função para salvar dados no CSV
def salvar_csv(numero, mensagem, resposta):
    file_exists = os.path.isfile(csv_filename)
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Numero', 'Mensagem Recebida', 'Resposta Enviada'])
        writer.writerow([numero, mensagem, resposta])

# Função para gerar resposta via OpenAI
def gerar_resposta_ia(pergunta):
    prompt = f"""
Você é uma secretária virtual simpática da Clínica Bem-Querer Odontologia. Responda de forma clara, objetiva e acolhedora. 
Informações importantes da clínica:
- Horário de atendimento: Segunda a sexta das 8:00 às 19:00 e sábados das 9:00 às 16:00.
- Serviços: Ortodontia, Odontopediatria, Implantes, Atendimento a Pacientes Especiais, Trabalhamos com Sedação Endovenosa, Ortodontia, Alinhadores invisíveis, exclusivamente com Invisalign.
- Localização: Santo André, SP.

Pergunta: {pergunta}
"""
    resposta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Você é uma secretária virtual da Clínica Bem-Querer Odontologia."},
            {"role": "user", "content": prompt}
        ]
    )
    return resposta["choices"][0]["message"]["content"].strip()

@app.route("/", methods=['POST'])
def index():
    numero = request.form.get('From')
    mensagem = request.form.get('Body').strip()

    # IA responde diretamente
    resposta_ia = gerar_resposta_ia(mensagem)
    
    # Salva no CSV
    salvar_csv(numero, mensagem, resposta_ia)

    # Responde no WhatsApp
    resp = MessagingResponse()
    resp.message(resposta_ia)

    response = Response(str(resp), mimetype='application/xml')
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
