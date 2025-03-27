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

# Tabela para armazenar histórico do chat
class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True)
    user_phone = db.Column(db.String(50))
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# Flask-Admin
admin = Admin(app, name='Bem-Querer Admin', template_mode='bootstrap3')
admin.add_view(ModelView(Clinic, db.session))
admin.add_view(ModelView(FAQ, db.session))
admin.add_view(ModelView(Context, db.session))
admin.add_view(ModelView(Lead, db.session))
admin.add_view(ModelView(ChatHistory, db.session))

# OpenAI Config
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# LangChain Config
llm = ChatOpenAI(temperature=0, model_name="gpt-4")

# Função para buscar o histórico recente do paciente
def buscar_historico(user_phone, limite=5):
    user_phone = user_phone.replace("whatsapp:", "")  # Remover prefixo Twilio
    historico = ChatHistory.query.filter_by(user_phone=user_phone).order_by(ChatHistory.timestamp.desc()).limit(limite).all()
    
    if not historico:
        return ""
    
    return "\n".join([f"Paciente: {msg.message}\nIA: {msg.response}" for msg in historico])

# Função para salvar a conversa
def salvar_conversa(user_phone, message, response):
    chat_entry = ChatHistory(user_phone=user_phone, message=message, response=response)
    db.session.add(chat_entry)
    db.session.commit()

# Ajuste do prompt para incluir histórico
def gerar_resposta_ia(pergunta, numero):
    historico = buscar_historico(numero)
    prompt = f"""Você é uma secretária virtual da Bem-Querer Odontologia.

    Aqui está o histórico da conversa:
    {historico}

    Agora, o usuário enviou uma nova pergunta:
    {pergunta}

    Responda com clareza e carinho."""
    resposta = llm.invoke(prompt)
    salvar_conversa(numero, pergunta, resposta)
    return resposta

@app.route("/", methods=['POST'])
def index():
    numero = request.form.get('From')
    mensagem = request.form.get('Body').strip()
    resposta = gerar_resposta_ia(mensagem, numero)
    salvar_conversa(numero, mensagem, resposta)
    resp = MessagingResponse()
    resp.message(resposta)
    return Response(str(resp), mimetype='application/xml'), 200

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
