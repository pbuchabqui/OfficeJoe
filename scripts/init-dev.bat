@echo off
REM Script de inicializacao para desenvolvimento em Windows

setlocal enabledelayedexpansion

echo.
echo =====================================
echo   OfficeJoe - Development Setup
echo =====================================
echo.

REM 1. Verificar Docker
echo [1/4] Verificando Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo X Docker nao encontrado
    exit /b 1
)

REM Detectar qual comando usar (novo: docker compose ou antigo: docker-compose)
set DOCKER_COMPOSE=
docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    set DOCKER_COMPOSE=docker compose
) else (
    docker-compose --version >nul 2>&1
    if %errorlevel% equ 0 (
        set DOCKER_COMPOSE=docker-compose
    ) else (
        echo X Docker Compose nao encontrado
        echo Instale Docker Compose: https://docs.docker.com/compose/install/
        exit /b 1
    )
)

echo OK - Docker encontrado (usando: %DOCKER_COMPOSE%)
echo.

REM 2. Criar .env
echo [2/4] Criando arquivo .env...
if not exist .env (
    copy .env.example .env
    echo OK - .env criado
) else (
    echo AVISO - .env ja existe (nao sobrescrito)
)
echo.

REM 3. Iniciar Docker
echo [3/4] Iniciando servicos Docker...
%DOCKER_COMPOSE% -f docker-compose.yml -f docker-compose.dev.yml up -d --build
echo OK - Docker iniciado
echo.

REM 4. Aguardar backend
echo [4/4] Aguardando backend ficar pronto...
setlocal enabledelayedexpansion
set "attempts=0"
:wait_backend
curl -f http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo OK - Backend pronto
    goto setup_complete
)
set /a "attempts+=1"
if !attempts! gtr 30 (
    echo X Backend nao respondeu no tempo limite
    exit /b 1
)
timeout /t 2 /nobreak
goto wait_backend

:setup_complete
echo.
echo =====================================
echo   Setup Completo!
echo =====================================
echo.

echo Servicos disponiveis:
echo   Frontend:      http://localhost:3000
echo   API:           http://localhost:8000
echo   API Docs:      http://localhost:8000/docs
echo   MinIO:         http://localhost:9001
echo   Flower:        http://localhost:5555
echo.

echo Credenciais padrao:
echo   Email:         admin@example.com
echo   Senha:         admin123
echo.

echo Proximos passos:
echo   1. Abrir http://localhost:3000
echo   2. Fazer login
echo   3. Criar primeiro processo
echo   4. Fazer upload de PDF
echo.

echo Ver logs:
echo   docker-compose logs -f backend
echo   docker-compose logs -f celery_worker
echo   docker-compose logs -f frontend
echo.

echo Parar:
echo   docker-compose down
echo.
