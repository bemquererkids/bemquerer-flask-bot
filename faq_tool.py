
# tools/faq_tool.py
from langchain.tools import Tool
from models.models import FAQ

def buscar_resposta_faq_tool(pergunta):
    faqs = FAQ.query.all()
    for faq in faqs:
        if pergunta.lower() in faq.question.lower():
            return faq.answer
    return "Não encontrei nada na base de perguntas frequentes."

faq_tool = Tool(
    name="FAQ Tool",
    func=buscar_resposta_faq_tool,
    description="Busca uma resposta na FAQ da clínica com base em uma pergunta do usuário."
)
