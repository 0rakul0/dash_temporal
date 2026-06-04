# Deploy do dashboard temporal

Esta pasta contem uma versao enxuta do dashboard temporal para deploy no Render.

## Arquivos incluidos

- `app.py`: ponto de entrada do Dash.
- `requirements.txt`: dependencias necessarias para rodar o painel.
- `analise_temporal/`: modulos usados pelo dashboard em tempo de execucao.
- `saida/analises/RJ/retornos_apos_exoneracao.csv`: base de retornos.
- `saida/analises/RJ/movimentacoes_pessoas.parquet`: base de movimentacoes.

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
