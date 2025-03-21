from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def index():
    print("=== Nova requisição recebida ===")
    print("Método:", request.method)
    print("Headers:", dict(request.headers))
    print("Body:", request.get_data(as_text=True))

    # Cria resposta TwiML
    resp = MessagingResponse()
    resp.message("Recebido com sucesso pela Bem-Querer Bot! :)")

    response = Response(str(resp), mimetype='application/xml')
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
