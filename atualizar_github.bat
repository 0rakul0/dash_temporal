@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Executa sempre a partir da pasta onde este arquivo esta localizado.
cd /d "%~dp0"

set "REPO=%CD%"
set "LOG_DIR=%LOCALAPPDATA%\dash_temporal"
set "LOG_FILE=%LOG_DIR%\git_sync.log"
set "LOCK_DIR=%TEMP%\dash_temporal_git_sync.lock"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

rem Impede execucoes simultaneas pelo Agendador de Tarefas.
mkdir "%LOCK_DIR%" 2>nul
if errorlevel 1 (
    >>"%LOG_FILE%" echo [%date% %time%] Outra sincronizacao ja esta em andamento.
    exit /b 1
)

call :sincronizar >>"%LOG_FILE%" 2>&1
set "RESULTADO=%ERRORLEVEL%"

rmdir "%LOCK_DIR%" 2>nul
exit /b %RESULTADO%

:sincronizar
echo.
echo ============================================================
echo [%date% %time%] Iniciando sincronizacao de "%REPO%"

where git >nul 2>&1
if errorlevel 1 (
    echo ERRO: git.exe nao foi encontrado no PATH.
    exit /b 10
)

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo ERRO: a pasta nao e um repositorio Git.
    exit /b 11
)

for /f "delims=" %%B in ('git branch --show-current') do set "BRANCH=%%B"
if not defined BRANCH (
    echo ERRO: nao foi possivel identificar a branch atual.
    exit /b 12
)

echo Branch: %BRANCH%

echo Consolidando dados antes da sincronizacao...
python scripts\consolidar_dados.py
if errorlevel 1 (
    echo ERRO: falha ao consolidar os dados.
    exit /b 40
)

git add -A
if errorlevel 1 (
    echo ERRO: falha ao adicionar as alteracoes.
    exit /b 20
)

git diff --cached --quiet
if errorlevel 1 (
    for /f "delims=" %%D in ('powershell.exe -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"') do set "AGORA=%%D"
    git commit -m "Atualizacao automatica - !AGORA!"
    if errorlevel 1 (
        echo ERRO: falha ao criar o commit.
        exit /b 21
    )
) else (
    echo Nenhuma alteracao local para criar commit.
)

git ls-remote --exit-code --heads origin "%BRANCH%" >nul 2>&1
if not errorlevel 1 (
    git pull --rebase origin "%BRANCH%"
    if errorlevel 1 (
        echo ERRO: falha no pull --rebase. Verifique conflitos no repositorio.
        exit /b 30
    )
) else (
    echo A branch ainda nao existe no remoto; sera criada no primeiro push.
)

git push --set-upstream origin "%BRANCH%"
if errorlevel 1 (
    echo ERRO: falha ao enviar as alteracoes ao GitHub.
    exit /b 31
)

echo [%date% %time%] Sincronizacao concluida com sucesso.
exit /b 0
