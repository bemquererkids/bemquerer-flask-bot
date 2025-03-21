from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
import os
import csv

app = Flask(__name__)

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
        writer.writerow([data['numero'], data['nome'], data['servico'], data['disponibilidade']])

@app.route("/", methods=['POST'])
def index():
    numero = request.form.get('From')
    mensagem = request.form.get('Body').strip()
    
    if numero not in conversas:
        conversas[numero] = {'etapa': 1, 'numero': numero}

    etapa = conversas[numero]['etapa']
    resp = MessagingResponse()

    if etapa == 1:
        resp.message("Olá! Para começarmos, qual é o seu nome?")
        conversas[numero]['etapa'] = 2
    elif etapa == 2:
        conversas[numero]['nome'] = mensagem
        resp.message("Obrigado, {}! Qual serviço você deseja? (Ex: Ortodontia, Odontopediatria, Implante...)".format(mensagem))
        conversas[numero]['etapa'] = 3
    elif etapa == 3:
        conversas[numero]['servico'] = mensagem
        resp.message("Perfeito! Qual sua disponibilidade para agendamento?")
        conversas[numero]['etapa'] = 4
    elif etapa == 4:
        conversas[numero]['disponibilidade'] = mensagem
        resp.message("Ótimo! Suas informações foram registradas. Em breve nossa equipe entrará em contato. 😊")
        # Salvar no CSV
        salvar_csv(conversas[numero])
        # Remover do dicionário para próxima conversa
        del conversas[numero]

    response = Response(str(resp), mimetype='application/xml')
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
