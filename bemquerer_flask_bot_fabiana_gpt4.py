from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
import os
import csv
import openai
import time
import random

app = Flask(__name__)

# Configuração OpenAI usando variável de ambiente
openai.api_key = os.getenv("OPENAI_API_KEY")

csv_filename = "leads.csv"

def salvar_csv(numero, mensagem, resposta):
    file_exists = os.path.isfile(csv_filename)
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Numero', 'Mensagem Recebida', 'Resposta Enviada'])
        writer.writerow([numero, mensagem, resposta])

def gerar_resposta_ia(pergunta):
    prompt = f"""
Você é Fabiana, secretária virtual da Clínica Bem-Querer Odontologia. 

Perfil:
- Carinhosa, atenciosa e acolhedora.
- Especialista em CRC, vendas, administração e Saúde Bucal (TSB).
- Conhecedora de todos os procedimentos e especialidades da clínica.
- Só responde temas da Clínica Bem-Querer Odontologia.
- Se a pergunta não for sobre a clínica, responda educadamente que não possui informação sobre o tema.

Informações da Clínica:
- Atendimento: Seg-Sex das 8h às 19h, Sáb das 9h às 16h.
- Serviços: Ortodontia, Odontopediatria, Implantes, Pacientes Especiais, Sedação Endovenosa, Invisalign.
- Localização: Rua: Siqueira Campos,1068 - Siqueira Campos -Santo André - SP.

Pergunta: {pergunta}
"""
    resposta = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "Você é Fabiana, secretária virtual simpática e especialista da Clínica Bem-Querer Odontologia."},
            {"role": "user", "content": prompt}
        ]
    )
    return resposta["choices"][0]["message"]["content"].strip()

@app.route("/", methods=['POST'])
def index():
    numero = request.form.get('From')
    mensagem = request.form.get('Body').strip()

    resposta_ia = gerar_resposta_ia(mensagem)
    
    salvar_csv(numero, mensagem, resposta_ia)

    delay = random.randint(2, 4)
    time.sleep(delay)

    resp = MessagingResponse()
    resp.message(resposta_ia)

    response = Response(str(resp), mimetype='application/xml')
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
