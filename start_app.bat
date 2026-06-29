@echo off
setlocal EnableExtensions

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERRO: Python da virtualenv nao encontrado em .venv\Scripts\python.exe
    pause
    exit /b 10
)

if not exist "saida\consolidado\movimentacoes.parquet" (
    echo ERRO: movimentacoes.parquet nao encontrado em saida\consolidado
    echo Sincronize o consolidado a partir do projeto fonte antes de iniciar o app.
    pause
    exit /b 20
)

if not exist "saida\consolidado\retornos.parquet" (
    echo ERRO: retornos.parquet nao encontrado em saida\consolidado
    echo Sincronize o consolidado a partir do projeto fonte antes de iniciar o app.
    pause
    exit /b 21
)

echo Iniciando painel Flask com base consolidada local...
.venv\Scripts\python.exe app.py
pause
