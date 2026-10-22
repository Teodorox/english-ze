# English Zé

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

As tabelas são criadas sozinhas quando o app sobe. Mudanças na estrutura do banco ficam em `app/migrations/` (arquivos numerados, aplicados em ordem uma vez só).

Vindo da versão com SQLite? Antes de criar qualquer conta, `.venv\Scripts\python importar_sqlite.py` copia o `data/english.db` (cards, progresso, revisões, sequência e diário) pro PostgreSQL e confere as contagens; o arquivo antigo não é alterado. Os dados entram sem dono: depois de criar a sua conta, rode `contas.py assumir-dados SEU-EMAIL` (seção abaixo).

O navegador abre em http://127.0.0.1:8001 (se estiver ocupada, ele usa a próxima porta livre; ou escolha com `--port 9000`). Na primeira vez, e sempre que o código do app mudar, o `run.py` gera o app React sozinho (`npm ci` + `npm run build` em `web/`).

Use **Chrome, Edge ou Safari**: o reconhecimento de voz não funciona no Firefox.

### Contas

Cada pessoa tem a própria conta (e-mail e senha), com cards, progresso e diário só dela. O cadastro **só funciona com código de convite**, que você cria no terminal deste computador:

```powershell
.venv\Scripts\python contas.py convite --para "Professora Ana"   # código de uso único, ex.: K7QX-M2PA
.venv\Scripts\python contas.py convites                          # convites e quem usou
.venv\Scripts\python contas.py listar                            # contas
.venv\Scripts\python contas.py redefinir-senha EMAIL             # pra quem esqueceu (desconecta os aparelhos)
.venv\Scripts\python contas.py descricao EMAIL "texto"           # como a IA deve tratar essa pessoa na correção
.venv\Scripts\python contas.py assumir-dados EMAIL               # dados sem dono (da versão antiga) passam pra essa conta
```

A pessoa abre o app, toca em **Criar conta** e usa o código. Em **Ajustes → Conta** dá pra mudar o nome, trocar a senha, sair dos outros aparelhos e apagar a conta.

Segurança: as senhas são guardadas com Argon2 (nunca a senha em si), o login dura 30 dias num cookie protegido, e depois de várias tentativas erradas o e-mail e o IP ficam bloqueados por um tempo. O app também manda cabeçalhos de segurança (CSP, sem iframes etc.), recusa pedidos vindos de outros sites e limita o tamanho dos envios.

### No celular

Com o celular no mesmo Wi-Fi, dê dois cliques em **English Ze (celular).bat** (ou rode `.venv\Scripts\python run.py --lan`) e abra no celular o endereço `https://...` que aparece no terminal. Na primeira vez, o Windows pergunta se libera o Python no firewall: permita só em **redes privadas**.

O `--lan` serve em HTTPS com um certificado autoassinado (gerado em `data/certs/`), que é o que libera o microfone no celular. Por isso o navegador avisa que a conexão "não é particular": toque em **Mostrar detalhes → visitar este site**.

### Compartilhar pela internet (túnel)

1. Crie um convite pra pessoa (seção **Contas**) e mande o código.
2. Dê dois cliques em **Compartilhar com professora.bat** (ou rode `.venv\Scripts\python run.py --tunnel --port 8100`). Precisa do `cloudflared`: `winget install Cloudflare.cloudflared`.
3. O link `https://....trycloudflare.com` aparece na janela e já fica copiado: é só colar na mensagem. A pessoa cria a conta com o convite e, das próximas vezes, só entra.

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

As frases vêm das **trilhas** (`data/tracks/`): uma por objetivo do primeiro acesso, mais a `base` que todo mundo recebe, cada uma dividida em situações (no aeroporto, no hotel...) e níveis (iniciante e básico). No primeiro acesso a pessoa ganha as trilhas dos objetivos que escolheu, a partir do nível dela; mudar os objetivos em Ajustes acrescenta as trilhas novas sem apagar nada. Frases novas escritas nos arquivos chegam a todas as contas quando o servidor sobe de novo.

O tempo por dia define o tamanho do estudo: de 3 frases novas (5 min) a 15 (30 min), com um teto de revisões. Quando as revisões acumulam, as frases novas diminuem até a pessoa pôr em dia. Seus erros do diário e as frases que você minera entram na fila antes das trilhas.

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
- `app/auth.py`: contas, senhas (Argon2), sessões e limite de tentativas
- `app/security.py`: cabeçalhos de segurança, checagem de origem e limite de tamanho dos envios
- `contas.py`: convites e administração das contas pelo terminal
- `app/tutor.py`: correção com o Claude (prompt e formato da resposta)
- `app/db.py`: conexão com o PostgreSQL (pool), migrações e o "hoje" no fuso do usuário
- `app/migrations/`: estrutura do banco, um arquivo SQL numerado por mudança
- `importar_sqlite.py`: copia os dados da versão antiga (SQLite) pro PostgreSQL
- `web/src/pages/`: uma tela por aba
- `web/src/components/`: peças reutilizáveis (flashcard, anéis, controles no estilo iOS)
- `web/src/lib/`: lógica pura com testes (fila de estudo, pronúncia, datas, estatísticas)
- `web/src/styles/tokens.css`: cores dos temas claro e escuro
