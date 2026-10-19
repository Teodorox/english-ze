# English Ze

Plataforma pessoal pra estudar inglês em sessões curtas, focada em **entender streamers americanos** e **conversar**.

## Como rodar

```powershell
# primeira vez
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# todo dia
.venv\Scripts\python run.py
```

O navegador abre em http://127.0.0.1:8001 (se estiver ocupada, ele usa a próxima porta livre; ou escolha com `--port 9000`). Use **Chrome ou Edge**: o reconhecimento de voz só funciona neles, e o Edge tem as vozes "Natural", que soam mais humanas.

### Login

Defina `ENGLISH_ZE_PASSWORD` no `.env` e o app passa a pedir senha (o navegador lembra por 30 dias). Depois de 5 senhas erradas, o IP fica bloqueado por 5 minutos. Trocar a senha desconecta todos os aparelhos.

### No celular

Defina a senha (seção acima) e, com o celular no mesmo Wi-Fi, rode `.venv\Scripts\python run.py --lan` e abra no celular o endereço `https://...` que aparece no terminal. Na primeira vez, o Windows pergunta se libera o Python no firewall: permita só em **redes privadas**.

O `--lan` serve em HTTPS com um certificado autoassinado (gerado em `data/certs/`), que é o que libera o microfone no celular. Por isso o navegador avisa que a conexão "não é particular": toque em **Avançado → Continuar**. Sem senha definida, o `--lan` se recusa a iniciar.

### IA (opcional)

Copie `.env.example` para `.env` e coloque sua `ANTHROPIC_API_KEY`. O Diário passa a corrigir seus textos automaticamente, e cada erro vira um card na categoria **meus-erros**. O modelo padrão é o `claude-haiku-5-5`, que custa centavos por mês; dá pra trocar com `ENGLISH_ZE_MODEL`. Sem chave, tudo funciona normalmente e o Diário usa o botão 📋 de copiar prompt.

## O que tem

| Aba | Método | Pra quê |
|---|---|---|
| **Estudar** | Repetição espaçada (SM-2, igual ao Anki) | Revisar frases logo antes de esquecer. O modo 🎧 *Ouvir* esconde o texto e treina listening. |
| **Falar** | Shadowing + reconhecimento de voz | Ouvir, imitar, gravar e ver quais palavras o reconhecimento entendeu. |
| **Minerar** | Sentence mining | Anotar frases das lives e transformar em cards. |
| **Cards** | — | Buscar, ouvir e apagar cards. |
| **Diário** | Produção escrita + correção | Escrever umas linhas por dia; a IA corrige e transforma os erros em cards. |
| **Progresso** | — | Sequência de dias, revisões e cards dominados. |

O deck inicial (`data/seed_cards.json`) tem cerca de 70 frases em 4 categorias: gírias de streamer, fala rápida (gonna, wanna, finna...), conversa básica e inglês para trabalho em dev.

## Rotina sugerida (10 min)

1. **5 min:** Estudar (revisões do dia + novos)
2. **3 min:** Falar (shadowing de 2 ou 3 frases)
3. **2 min:** assistindo uma live? Minere 1 ou 2 frases que você não entendeu

## Desenvolvimento

```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

- `app/srs.py`: algoritmo de repetição espaçada
- `app/main.py`: API (FastAPI)
- `app/auth.py`: login por senha (cookie assinado + limite de tentativas)
- `app/tutor.py`: correção com o Claude (prompt e formato da resposta)
- `app/db.py`: SQLite (`data/english.db`, criado no primeiro uso)
- `static/`: frontend (HTML/CSS/JS puro)
