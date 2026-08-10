# DOU RJ - Analise Temporal de Publicacoes

Esta pasta contem uma versao enxuta do painel temporal para deploy. O app atual
e uma aplicacao Flask com templates HTML, assets estaticos e APIs JSON para
consulta dos dados consolidados.

URL publica: <https://dash-temporal.onrender.com/>

Este repositorio e o ambiente de deploy. O desenvolvimento principal fica em
`D:\github\exoneracoes_nomeacoes_dou`; a consolidacao e a limpeza dos dados
acontecem la. Aqui, ficam apenas o app, seus arquivos estaticos e os arquivos
consolidados consumidos pelo dashboard.

## Arquivos incluidos

- `app.py`: ponto de entrada Flask.
- `requirements.txt`: dependencias necessarias para rodar o painel.
- `templates/`, `static/` e `assets/`: interface web do painel.
- `analise_temporal/`: modulos usados pelo app em tempo de execucao.
- `saida/consolidado/retornos.parquet`: base consolidada de retornos.
- `saida/consolidado/movimentacoes.parquet`: base consolidada de movimentacoes.
- `Dockerfile` e `.dockerignore`: pacote de container para deploy.
- `.gitlab-ci.yml`, `deployment.yaml`, `service.yaml` e `ingress.yaml`: base de
  deploy GitLab/Kubernetes no padrao usado pelo IPEA.

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
Starting Flask app
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

## Docker local

Construa a imagem:

```powershell
docker build -t dash-temporal .
```

Rode o container:

```powershell
docker run --rm -p 8052:8052 dash-temporal
```

Depois acesse:

```text
http://127.0.0.1:8052
```

## GitLab/Kubernetes

Os arquivos `.gitlab-ci.yml`, `deployment.yaml`, `service.yaml` e `ingress.yaml`
seguem o mesmo desenho do exemplo `rag-main`: build com Kaniko, imagem no
registry do GitLab, deploy com `kubectl`, Service interno na porta 80 e Ingress
HTTPS em:

```text
https://<namespace>-<projeto>-dev.ipea.gov.br
```

Antes do primeiro deploy no cluster, confira no Rancher/GitLab:

- se o namespace `<namespace>-<projeto>` existe;
- se o secret `ipea-star-certificate` esta disponivel no namespace;
- se o secret `registry-gitlab-ipealegis` existe para puxar a imagem;
- se o contexto `ipealegis/k8s-agents:ipealegis` e o correto para este projeto.
