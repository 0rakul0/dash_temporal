# Deploy do dashboard temporal

Esta pasta contem uma versao enxuta do dashboard temporal para deploy no Render.

URL publica: <https://dash-temporal.onrender.com/>

Este repositorio e o ambiente de deploy. O desenvolvimento principal fica em
`D:\github\exoneracoes_nomeacoes_dou`; a consolidacao e a limpeza dos dados
acontecem la. Aqui, ficam apenas o app, seus arquivos estaticos e os arquivos
consolidados consumidos pelo dashboard.

## Arquivos incluidos

- `app.py`: ponto de entrada do Dash.
- `requirements.txt`: dependencias necessarias para rodar o painel.
- `analise_temporal/`: modulos usados pelo dashboard em tempo de execucao.
- `saida/consolidado/retornos.parquet`: base consolidada de retornos.
- `saida/consolidado/movimentacoes.parquet`: base consolidada de movimentacoes.

## Fluxo de dados

Quando a base analitica mudar no projeto principal, copie apenas os arquivos de
`saida/consolidado/` para este repositorio antes do deploy ou da sincronizacao
com o GitHub.

Nao devem entrar aqui:

- `LAKE/`, `diarios_oficiais/` e demais insumos brutos da coleta.
- `saida/analises/` e outros artefatos intermediarios de processamento.
- scripts de extracao, deduplicacao, consolidacao ou analise incremental.

## Render

Crie um Web Service apontando para este repositorio e configure:

```text
Root Directory:
deixe em branco
```

```text
Build Command:
pip install -r requirements.txt
```

```text
Start Command:
bash start.sh
```

O Render define a variavel `PORT` automaticamente. O app precisa escutar em `0.0.0.0:$PORT` para ficar acessivel publicamente.

Se o servico foi criado manualmente pelo painel do Render, confira se o campo
`Start Command` na interface tambem foi atualizado para `bash start.sh`.
Alterar `render.yaml` no repositorio nao necessariamente muda um servico manual
ja criado.

Opcionalmente, configure o Health Check Path como:

```text
/healthz
```

Se aparecer `No open ports detected`, aguarde alguns instantes e procure no log
pelas linhas emitidas por `start.sh`:

```text
Starting Dash app
PORT=...
PWD=...
Python=...
```

Se essas linhas nao aparecem, o Render ainda esta usando outro Start Command ou
outro diretorio raiz.

## Teste local

Dentro desta pasta:

```powershell
python app.py
```

Depois acesse:

```text
http://127.0.0.1:8052
```
