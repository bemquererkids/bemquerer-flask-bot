
# secretaria_ia/agents/langchain_agent.py

from langchain.agents import initialize_agent, AgentType
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from tools.faq_tool import faq_tool
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Inicializa o modelo LLM
llm = ChatOpenAI(
    temperature=0,
    model_name="gpt-4",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# Inicializa memória da conversa
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Inicializa o agente com a ferramenta de FAQ
agent = initialize_agent(
    tools=[faq_tool],
    llm=llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True
)

# Interface para responder com a Clara inteligente
def clara_responde(pergunta):
    resposta = agent.run(pergunta)
    return resposta
