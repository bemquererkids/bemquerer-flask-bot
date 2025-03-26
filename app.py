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
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuração Flask e PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

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
    message = db.Column(db.Text)  # ✅ Esta linha precisa estar presente
    response = db.Column(db.Text)  # ✅ Esta linha também
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

# Variáveis globais
contexto_clinica = ""
faq_list = []

# Funções auxiliares
def carregar_contexto():
    contexto = Context.query.first()
    return contexto.content if contexto else ""

def carregar_faq():
    faqs = FAQ.query.all()
    return [{'Pergunta': f.question, 'Resposta': f.answer} for f in faqs]

def salvar_lead(numero, mensagem, resposta):
    lead = Lead(
        clinic_id=1,
        name="",
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

def gerar_resposta_ia(pergunta):
    resposta = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": contexto_clinica},
            {"role": "user", "content": pergunta}
        ]
    )
    return resposta.choices[0].message.content.strip()

# Rota principal com suporte a GET
@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return "🚀 API da secretária virtual está ativa!", 200

    numero = request.form.get('From')
    mensagem = request.form.get('Body').strip()

    print(f"📥 Mensagem recebida de {numero}: {mensagem}")

    resposta_faq = verificar_faq(mensagem)

    if resposta_faq:
        resposta = resposta_faq
        print("✅ Resposta enviada pelo FAQ (Alta similaridade)")
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
    with app.app_context():
        db.create_all()
        print("✅ Tabelas criadas ou atualizadas!")
        contexto_clinica = carregar_contexto()
        faq_list = carregar_faq()
        print("🚀 Contexto e FAQ carregados!")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
