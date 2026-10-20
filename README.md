# English Ze

Plataforma pra estudar inglês em sessões curtas, focada em **entender streamers americanos** e **conversar**. Visual no padrão iOS (vidro fosco, títulos grandes, abas com ícones), com tema claro e escuro automáticos. No computador (telas a partir de 1024px), o app ganha barra lateral, telas em colunas e atalhos de teclado; no celular e no tablet, continua com a barra de abas embaixo.

## Como rodar

Precisa do **Python 3.13**, do **Node.js** (usado pra gerar o app na primeira vez) e do **PostgreSQL 17**.

```powershell
# primeira vez
winget install PostgreSQL.PostgreSQL.17   # o banco de dados (roda como serviço do Windows)
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# todo dia: dois cliques em "English Ze.bat", ou
.venv\Scripts\python run.py
```

Na primeira vez, crie o usuário e os bancos do app (com a senha de superusuário escolhida na instalação) e coloque `DATABASE_URL` e `TEST_DATABASE_URL` no `.env` (modelo no `.env.example`):

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h localhost -U postgres -c "CREATE ROLE english_ze LOGIN CREATEDB PASSWORD 'escolha-uma-senha'"
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h localhost -U postgres -c "CREATE DATABASE english_ze OWNER english_ze" -c "CREATE DATABASE english_ze_test OWNER english_ze"
```

As tabelas e o deck inicial são criados sozinhos quando o app sobe. Mudanças na estrutura do banco ficam em `app/migrations/` (arquivos numerados, aplicados em ordem uma vez só).

Vindo da versão com SQLite? `.venv\Scripts\python importar_sqlite.py` copia o `data/english.db` (cards, progresso, revisões, sequência e diário) pro PostgreSQL e confere as contagens; o arquivo antigo não é alterado. Pra um perfil: `--profile NOME`.

O navegador abre em http://127.0.0.1:8001 (se estiver ocupada, ele usa a próxima porta livre; ou escolha com `--port 9000`). Na primeira vez, e sempre que o código do app mudar, o `run.py` gera o app React sozinho (`npm ci` + `npm run build` em `web/`).

Use **Chrome, Edge ou Safari**: o reconhecimento de voz não funciona no Firefox.

### Login

Defina `ENGLISH_ZE_PASSWORD` no `.env` e o app passa a pedir senha (o navegador lembra por 30 dias). Os dados (a API) ficam protegidos; sem login, o app mostra a tela de entrada. Depois de 5 senhas erradas, o IP fica bloqueado por 5 minutos. Trocar a senha desconecta todos os aparelhos.

### No celular

Defina a senha (seção acima) e, com o celular no mesmo Wi-Fi, dê dois cliques em **English Ze (celular).bat** (ou rode `.venv\Scripts\python run.py --lan`) e abra no celular o endereço `https://...` que aparece no terminal. Na primeira vez, o Windows pergunta se libera o Python no firewall: permita só em **redes privadas**.

O `--lan` serve em HTTPS com um certificado autoassinado (gerado em `data/certs/`), que é o que libera o microfone no celular. Por isso o navegador avisa que a conexão "não é particular": toque em **Mostrar detalhes → visitar este site**. Sem senha definida, o `--lan` se recusa a iniciar.

### Compartilhar com outra pessoa (perfil + túnel)

Cada perfil é uma cópia separada do app, com senha e progresso próprios: os dados ficam no banco `english_ze_NOME` (criado sozinho na primeira vez) e a configuração em `data/profiles/NOME/` (ignorado pelo git).

1. Crie `data/profiles/NOME/.env` com pelo menos:
   ```
   ENGLISH_ZE_PASSWORD=senha-dessa-pessoa
   # opcional: como a IA deve tratar essa pessoa na correção
   ENGLISH_ZE_LEARNER=Professora de inglês, escreve em inglês fluente...
   ```
2. Dê dois cliques em **Compartilhar com professora.bat** (para outro perfil, rode o comando abaixo). Precisa do `cloudflared`: `winget install Cloudflare.cloudflared`.
   ```powershell
   .venv\Scripts\python run.py --profile NOME --tunnel --port 8100
   ```
3. O link `https://....trycloudflare.com` aparece na janela e já fica copiado: é só colar na mensagem junto com a senha.

O link funciona de qualquer lugar e tem HTTPS válido (sem aviso, microfone liberado), mas só enquanto a janela estiver aberta, e **muda a cada vez** que você reinicia. A correção por IA usa a sua chave da API: defina um limite de gasto no console da Anthropic.

### Checar pronúncia no iPhone (opcional)

O Safari do iPhone pode recusar o reconhecimento de voz do navegador. Com o Whisper instalado, o app grava a sua fala e transcreve no servidor, o que funciona em qualquer navegador e é mais preciso:

```powershell
.venv\Scripts\python -m pip install -r requirements-voice.txt
```

Na primeira checagem ele baixa o modelo `base.en` (~150 MB) para `data/models/`; depois cada frase leva menos de 1 segundo. Sem o Whisper, o app usa o reconhecimento de voz do navegador.

### IA (opcional)

Copie `.env.example` para `.env` e coloque sua `ANTHROPIC_API_KEY`. O Diário passa a corrigir seus textos automaticamente, e cada erro vira um card na categoria **meus-erros**. O modelo padrão é o `claude-haiku-5-5`, que custa centavos por mês; dá pra trocar com `ENGLISH_ZE_MODEL`. Sem chave, tudo funciona e o Diário oferece o botão de copiar o prompt.

## O que tem

| Aba | Método | Pra quê |
|---|---|---|
| 🔒 **Lock In** (Estudar) | Repetição espaçada (SM-2, igual ao Anki) | Revisar frases logo antes de esquecer. O modo *Ouvir* esconde o texto e treina listening. Notas: L / MID / W / GOAT. |
| 🎤 **Mic Check** (Falar) | Shadowing + reconhecimento de voz | Ouvir, imitar, gravar e ver a pontuação de pronúncia palavra por palavra. |
| ✂️ **Clip It** (Minerar) | Sentence mining | Anotar frases das lives e transformar em cards (uma por vez ou em lote). |
| 🗂️ **The Vault** (Cards) | — | Buscar, filtrar, ouvir e apagar cards, e ver quando cada um volta. |
| 💬 **Daily Yap** (Diário) | Produção escrita + correção | Escrever umas linhas por dia; a IA corrige e transforma os erros em cards. |
| 📊 **Stats** (Progresso) | — | Anéis de meta diária e semana, sequência de dias e gráfico de 14 dias. |

O deck inicial (`data/seed_cards.json`) tem cerca de 70 frases em 4 categorias: gírias de streamer, fala rápida (gonna, wanna, finna...), conversa básica e inglês para trabalho em dev. Seus erros do diário e as frases que você minera entram na fila antes do deck inicial.

## Rotina sugerida (10 min)

1. **5 min:** Lock In (revisões do dia + novos)
2. **3 min:** Mic Check (shadowing de 2 ou 3 frases)
3. **2 min:** assistindo uma live? Clip It em 1 ou 2 frases que você não entendeu

## Desenvolvimento

```powershell
# backend (os testes usam o banco do TEST_DATABASE_URL, que é apagado a cada teste)
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest

# frontend (outro terminal)
.venv\Scripts\python run.py        # backend em http://127.0.0.1:8001
cd web
npm install                         # primeira vez
npm run dev                         # React com recarga instantânea em http://localhost:5173
npm test                            # testes (Vitest)
npm run typecheck                   # checagem de tipos
```

A cada push, o GitHub Actions roda os testes do backend (com um PostgreSQL temporário) e do frontend (tipos, testes e build).

- `app/main.py`: API (FastAPI) e entrega do app React
- `app/web.py`: serve `web/dist` (arquivos com cache; endereços de tela devolvem o app)
- `app/srs.py`: algoritmo de repetição espaçada
- `app/auth.py`: login por senha (cookie assinado + limite de tentativas)
- `app/tutor.py`: correção com o Claude (prompt e formato da resposta)
- `app/db.py`: conexão com o PostgreSQL (pool), migrações e o "hoje" no fuso do usuário
- `app/migrations/`: estrutura do banco, um arquivo SQL numerado por mudança
- `importar_sqlite.py`: copia os dados da versão antiga (SQLite) pro PostgreSQL
- `web/src/pages/`: uma tela por aba
- `web/src/components/`: peças reutilizáveis (flashcard, anéis, controles no estilo iOS)
- `web/src/lib/`: lógica pura com testes (fila de estudo, pronúncia, datas, estatísticas)
- `web/src/styles/tokens.css`: cores dos temas claro e escuro
