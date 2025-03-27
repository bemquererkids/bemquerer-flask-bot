from flask_migrate import Migrate
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
from datetime import datetime
from dotenv import load_dotenv
import re
from langchain.agents import initialize_agent, Tool
from langchain_openai import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain.schema import SystemMessage
import pytz

load_dotenv()

app = Flask(__name__)

# Configuração Flask e PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

# Banco de Dados
db = SQLAlchemy(app)
migrate = Migrate(app, db)

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
    email = db.Column(db.String(100), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    special_needs = db.Column(db.Boolean, default=False)
    syndrome = db.Column(db.String(100), nullable=True)
    sedation = db.Column(db.Boolean, default=False)
    allergies = db.Column(db.Text, nullable=True)
    medications = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_contact = db.Column(db.DateTime, default=db.func.current_timestamp())

# Flask-Admin
admin = Admin(app, name='Bem-Querer Admin', template_mode='bootstrap3')
admin.add_view(ModelView(Clinic, db.session))
admin.add_view(ModelView(FAQ, db.session))
admin.add_view(ModelView(Context, db.session))
admin.add_view(ModelView(Lead, db.session))

# OpenAI Config
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# LangChain Config
llm = ChatOpenAI(temperature=0, model_name="gpt-4")

# Variáveis globais
contexto_clinica = ""
faq_list = []
nome_usuario = {}

# Funções auxiliares
def carregar_contexto():
    contexto = Context.query.first()
    return contexto.content if contexto else ""

def carregar_faq():
    faqs = FAQ.query.all()
    return [{'Pergunta': f.question, 'Resposta': f.answer} for f in faqs]

def obter_nome_salvo(numero):
    lead = Lead.query.filter_by(phone=numero).order_by(Lead.created_at.desc()).first()
    return lead.name if lead and lead.name else None

def salvar_lead(numero, mensagem, resposta):
    nome = nome_usuario.get(numero, obter_nome_salvo(numero) or "")
    lead = Lead(
        clinic_id=1,
        name=nome,
        phone=numero,
        email=None,
        birth_date=None,
        special_needs=False,
        syndrome=None,
        sedation=False,
        allergies=None,
        medications=None,
        notes=None,
        message=mensagem,
        response=resposta
    )
    db.session.add(lead)
    db.session.commit()
    print(f"💾 Lead salvo no banco: {numero}, {mensagem}")

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

def gerar_saudacao():
    agora = datetime.now(pytz.timezone("America/Sao_Paulo")).hour
    if agora < 12:
        return "Bom dia"
    elif 12 <= agora < 18:
        return "Boa tarde"
    else:
        return "Boa noite"

def responder_com_agente(pergunta):
    agente = initialize_agent(tools=[], llm=llm, agent=AgentType.OPENAI_FUNCTIONS, verbose=False)
    return agente.invoke(pergunta)

def gerar_resposta_ia(pergunta, numero):
    saudacao = gerar_saudacao()
    nome = nome_usuario.get(numero, obter_nome_salvo(numero) or "")
    resposta = responder_com_agente(pergunta)
    return f"{saudacao}, {nome}! {resposta.capitalize()}"

@app.route("/", methods=['POST'])
def index():
    numero = request.form.get('From')
    mensagem = request.form.get('Body').strip()
    resposta = gerar_resposta_ia(mensagem, numero)
    salvar_lead(numero, mensagem, resposta)
    resp = MessagingResponse()
    resp.message(resposta)
    return Response(str(resp), mimetype='application/xml'), 200

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        contexto_clinica = carregar_contexto()
        faq_list = carregar_faq()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
