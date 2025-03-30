# services/whatsapp_handler.py
from models.models import FAQ, Lead, Context
from app import db
import difflib
from agents.langchain_agent import clara_responde

# Busca resposta na FAQ com correspondência aproximada
def buscar_resposta_faq(pergunta):
    faqs = FAQ.query.all()
    perguntas = [faq.question.lower() for faq in faqs]
    resposta_certa = difflib.get_close_matches(pergunta.lower(), perguntas, n=1, cutoff=0.6)
    if resposta_certa:
        for faq in faqs:
            if faq.question.lower() == resposta_certa[0]:
                return faq.answer
    return None

# Busca dados do lead (nome, origem)
def buscar_lead(phone):
    phone_formatado = phone.replace("whatsapp:", "").strip()
    lead = Lead.query.filter(Lead.phone.ilike(f"%{phone_formatado}%")).first()
    if lead:
        return lead.name, lead.source
    return None, None

# Busca contexto salvo do usuário
def buscar_contexto(phone):
    contexto = Context.query.filter_by(user_phone=phone).first()
    return (contexto.last_interaction, contexto.last_response) if contexto else (None, None)

# Salva ou atualiza contexto
def salvar_contexto(phone, mensagem, resposta):
    contexto_existente = Context.query.filter_by(user_phone=phone).first()
    if contexto_existente:
        contexto_existente.last_interaction = mensagem
        contexto_existente.last_response = resposta
    else:
        novo_contexto = Context(user_phone=phone, last_interaction=mensagem, last_response=resposta)
        db.session.add(novo_contexto)
    db.session.commit()

# Função principal de resposta
def responder_mensagem(numero, mensagem):
    numero = numero.replace("whatsapp:", "").strip()
    mensagem = mensagem.strip().lower()

    nome, origem = buscar_lead(numero)
    ultima_interacao, ultima_resposta = buscar_contexto(numero)

    saudacao = "Olá"
    if nome:
        saudacao += f" {nome}, tudo bem?"
    else:
        saudacao += ", tudo bem?"

    resposta = buscar_resposta_faq(mensagem)

    if not resposta:
        if "consulta" in mensagem:
            resposta = f"{saudacao} Você deseja agendar uma consulta? Me diga se prefere manhã ou tarde."
        elif "endereço" in mensagem or "onde fica" in mensagem:
            resposta = "Estamos na Rua Siqueira Campos, 1068 - Vila Assunção, Santo André/SP. Próximo à Padaria Brasileira."
        elif ultima_interacao and mensagem != ultima_interacao and mensagem not in ["olá", "oi", "tudo bem?"]:
            resposta = f"{saudacao} Você quer continuar falando sobre '{ultima_interacao}' ou precisa de algo diferente?"
        else:
            # Se nada funcionar, usa a inteligência da Clara com LangChain
            resposta = clara_responde(mensagem)

    salvar_contexto(numero, mensagem, resposta)
    return resposta
