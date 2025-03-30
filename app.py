# app.py
from flask import Flask, request, Response
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente
load_dotenv()

# Inicialização Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

# Banco de Dados e Admin
db = SQLAlchemy(app)
migrate = Migrate(app, db)
admin = Admin(app, name='Bem-Querer Admin', template_mode='bootstrap3')

# Importa modelos e adiciona ao admin
from models.models import Clinic, FAQ, Lead, ChatHistory, Context
admin.add_view(ModelView(Clinic, db.session))
admin.add_view(ModelView(FAQ, db.session))
admin.add_view(ModelView(Lead, db.session))
admin.add_view(ModelView(ChatHistory, db.session))
admin.add_view(ModelView(Context, db.session))

# Importa serviço de resposta principal
from services.whatsapp_handler import responder_mensagem

# Rota principal para Twilio
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return "API rodando corretamente", 200

    numero = request.form.get("From")
    mensagem = request.form.get("Body")

    if not numero or not mensagem:
        return "Dados inválidos", 400

    resposta = responder_mensagem(numero, mensagem)

    resp = MessagingResponse()
    resp.message(resposta)
    return Response(str(resp), mimetype='application/xml'), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
