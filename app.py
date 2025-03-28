from flask_migrate import Migrate
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import os
import difflib
from openai import OpenAI
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import re
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

class Lead(db.Model):
    __tablename__ = 'leads'
    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinics.id'))
    name = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    source = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_contact = db.Column(db.DateTime, default=db.func.current_timestamp())

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True)
    user_phone = db.Column(db.String(50))
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class Context(db.Model):
    __tablename__ = 'context'
    id = db.Column(db.Integer, primary_key=True)
    user_phone = db.Column(db.String(50), nullable=False, unique=True)
    last_interaction = db.Column(db.Text, nullable=True)
    last_response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

# Flask-Admin
admin = Admin(app, name='Bem-Querer Admin', template_mode='bootstrap3')
admin.add_view(ModelView(Clinic, db.session))
admin.add_view(ModelView(FAQ, db.session))
admin.add_view(ModelView(Lead, db.session))
admin.add_view(ModelView(ChatHistory, db.session))
admin.add_view(ModelView(Context, db.session))

# OpenAI Config
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
llm = ChatOpenAI(temperature=0, model_name="gpt-4", openai_api_key=os.getenv("OPENAI_API_KEY"))

# Função para buscar resposta na FAQ com correspondência aproximada
def buscar_resposta_faq(pergunta):
    faqs = FAQ.query.all()
    perguntas = [faq.question.lower() for faq in faqs]
    resposta_certa = difflib.get_close_matches(pergunta.lower(), perguntas, n=1, cutoff=0.6)
    if resposta_certa:
        for faq in faqs:
            if faq.question.lower() == resposta_certa[0]:
                return faq.answer
    return None

# Função para capturar nome e origem do lead
def buscar_lead(phone):
    phone_formatado = phone.replace("whatsapp:", "").strip()
    lead = Lead.query.filter(Lead.phone.ilike(f"%{phone_formatado}%")).first()
    if lead:
        return lead.name, lead.source
    return None, None

# Função para buscar contexto do usuário
def buscar_contexto(phone):
    contexto = Context.query.filter_by(user_phone=phone).first()
    return (contexto.last_interaction, contexto.last_response) if contexto else (None, None)

# Função para salvar contexto
def salvar_contexto(phone, mensagem, resposta):
    contexto_existente = Context.query.filter_by(user_phone=phone).first()
    if contexto_existente:
        contexto_existente.last_interaction = mensagem
        contexto_existente.last_response = resposta
    else:
        novo_contexto = Context(user_phone=phone, last_interaction=mensagem, last_response=resposta)
        db.session.add(novo_contexto)
    db.session.commit()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return "API rodando corretamente", 200
    
    numero = request.form.get("From")
    if not numero:
        return "Número inválido", 400
    numero = numero.replace("whatsapp:", "").strip()
    
    mensagem = request.form.get("Body").strip()
    nome, origem = buscar_lead(numero)
    ultima_interacao, ultima_resposta = buscar_contexto(numero)
    
    saudacao = "Olá"
    if nome:
        saudacao += f" {nome}, tudo bem?"
    else:
        saudacao += ", tudo bem?"
    
    resposta = buscar_resposta_faq(mensagem)
    if not resposta:
        if "consulta" in mensagem.lower():
            resposta = f"{saudacao} Você deseja agendar uma consulta? Me informe um período que seja melhor para você: manhã ou tarde."
        elif "endereço" in mensagem.lower() or "onde fica" in mensagem.lower():
            resposta = "Estamos na Rua Siqueira Campos, 1068 - Vila Assunção, Santo André/SP. Próximo à Padaria Brasileira."
        elif ultima_interacao and ultima_resposta and mensagem.lower() != ultima_interacao.lower() and mensagem.lower() not in ["olá", "oi", "tudo bem?"]:
            resposta = f"{saudacao} Sobre nossa última conversa: '{ultima_interacao}'. Como posso te ajudar agora?"
        else:
            resposta = f"{saudacao} Como posso te ajudar hoje?"
    
    salvar_contexto(numero, mensagem, resposta)
    
    resp = MessagingResponse()
    resp.message(resposta)
    return Response(str(resp), mimetype='application/xml'), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
