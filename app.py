from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
import os
import csv
import openai

app = Flask(__name__)

# Configuração OpenAI
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Dicionário para armazenar o estado da conversa por número
conversas = {}

# Caminho do arquivo CSV
csv_filename = "leads.csv"

# Função para salvar dados no CSV
def salvar_csv(data):
    file_exists = os.path.isfile(csv_filename)
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Numero', 'Nome', 'Servico', 'Disponibilidade'])
        writer.writerow([data['numero'], data.get('nome', ''), data.get('servico', ''), data.get('disponibilidade', '')])

# Função para gerar resposta via OpenAI
def gerar_resposta_ia(pergunta):
    prompt = f"""
Você é uma secretária virtual simpática da Clínica Bem-Querer Odontologia. Responda de forma clara, objetiva e acolhedora. 
Informações importantes da clínica:
- Horário de atendimento: Segunda a sexta das 8:00 às 19:00 e sábados das 9:00 às 16:00.
- Serviços: Ortodontia, Odontopediatria, Implantes, Atendimento a Pacientes Especiais.
- Localização: Santo André, SP.

Pergunta: {pergunta}
"""
    resposta = openai.ChatCompletion.create(
        model="gpt-4",
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
    
    if numero not in conversas:
        conversas[numero] = {'etapa': 1, 'numero': numero}

    etapa = conversas[numero]['etapa']
    resp = MessagingResponse()

    # Fluxo principal
    if etapa == 1:
        resp.message("Olá! Para começarmos, qual é o seu nome?")
        conversas[numero]['etapa'] = 2
    elif etapa == 2:
        conversas[numero]['nome'] = mensagem
        resp.message(f"Obrigado, {mensagem}! Qual serviço você deseja? (Ex: Ortodontia, Odontopediatria, Implante...)")
        conversas[numero]['etapa'] = 3
    elif etapa == 3:
        conversas[numero]['servico'] = mensagem
        resp.message("Perfeito! Qual sua disponibilidade para agendamento?")
        conversas[numero]['etapa'] = 4
    elif etapa == 4:
        conversas[numero]['disponibilidade'] = mensagem
        resp.message("Ótimo! Suas informações foram registradas. Em breve nossa equipe entrará em contato. 😊")
        salvar_csv(conversas[numero])
        del conversas[numero]
    else:
        # Fora do fluxo: IA responde
        resposta_ia = gerar_resposta_ia(mensagem)
        resp.message(resposta_ia)

    response = Response(str(resp), mimetype='application/xml')
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
