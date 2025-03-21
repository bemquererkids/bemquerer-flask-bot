# Bem-Querer Bot - Flask + Twilio

Este projeto é um bot para responder mensagens do WhatsApp via Twilio, usando Flask e hospedado no Render.

## Como rodar localmente

1. Crie um ambiente virtual:
```
python3 -m venv venv
source venv/bin/activate
```

2. Instale as dependências:
```
pip install -r requirements.txt
```

3. Rode o app:
```
python app.py
```

## Para Deploy no Render

- Conecte seu repositório no Render.
- Configure:
  - **Environment**: Python
  - **Build Command**: `pip install -r requirements.txt`
  - **Start Command**: `python app.py`
- O Render cuidará do resto! Use o link gerado no Twilio Sandbox.
