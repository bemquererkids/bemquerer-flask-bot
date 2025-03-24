from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import os
import time
import random
import difflib
from openai import OpenAI

app = Flask(__name__)

# Configuração PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

db = SQLAlchemy(app)

# Modelos
class Clinic(db.Model):
    __tablename__ = 'clinics'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)

class FAQ(db.Model):
    __tablename__ = 'faq'
    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'))
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)

class Context(db.Model):
    __tablename__ = 'context'
    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'))
    content = db.Column(db.Text, nullable=False)

class Lead(db.Model):
    __tablename__ = 'leads'
    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'))
    name = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# Flask-Admin
admin = Admin(app, name='Bem-Querer Admin', template_mode='bootstrap3')
admin.add_view(ModelView(Clinic, db.session))
admin.add_view(ModelView(FAQ, db.session))
admin.add_view(ModelView(Context, db.session))
admin.add_view(ModelView(Lead, db.session))

@app.before_first_request
def create_tables():
    db.create_all()
    print("✅ Tabelas criadas!")

# OpenAI Config
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Carregar FAQ e contexto
def carregar_contexto():
    contexto = Context.query.first()
    return contexto.content if contexto else ""

def carregar_faq():
    faqs = FAQ.query.all()
    return [{'Pergunta': f.question, 'Resposta': f.answer} for f in faqs]

contexto_clinica = carregar_contexto()
faq_list = carregar_faq()

def salvar_lead(numero, mensagem, resposta):
    lead = Lead(
        clinic_id=1,
        name="",
        phone=numero,
        message=mensagem,
        response=resposta
    )
    db.session.add(lead)
    db.session.commit()
    print(f"💾 Lead salvo: {numero}, {mensagem}")

def verificar_faq(mensagem):
    mensagem = mensagem.lower().strip()
    melhor_similaridade = 0
    resposta_encontrada = None

    for row in faq_list:
        pergunta_faq = row['Pergunta'].lower().strip()
        similaridade = difflib.SequenceMatcher(None, pergunta_faq, mensagem).ratio()
        if similaridade > 0.6 and similaridade > melhor_similaridade:
            melhor_similaridade = similaridade
            resposta_encontrada = row['Resposta']

    return resposta_encontrada

def gerar_resposta_ia(pergunta):
    resposta = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": contexto_clinica},
            {"role": "user", "content": pergunta}
        ]
    )
    return resposta.choices[0].message.content.strip()

@app.route("/", methods=['POST'])
def index():
    numero = request.form.get('From')
    mensagem = request.form.get('Body').strip()

    print(f"📥 Mensagem recebida de {numero}: {mensagem}")

    resposta_faq = verificar_faq(mensagem)

    if resposta_faq:
        resposta = resposta_faq
        print("✅ Resposta do FAQ enviada")
    else:
        resposta = gerar_resposta_ia(mensagem)
        print("🤖 Resposta gerada pela OpenAI")

    salvar_lead(numero, mensagem, resposta)

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
