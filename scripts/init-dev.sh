#!/bin/bash
#
# Script de inicialização para desenvolvimento
# Cria .env, inicia Docker e configura usuário admin
#

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}═════════════════════════════════════════${NC}"
echo -e "${GREEN}  OfficeJoe - Development Setup${NC}"
echo -e "${GREEN}═════════════════════════════════════════${NC}\n"

# 1. Verificar Docker e Docker Compose
echo -e "${YELLOW}[1/5]${NC} Verificando Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker não encontrado${NC}"
    exit 1
fi

# Detectar qual comando usar (novo: docker compose ou antigo: docker-compose)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}✗ Docker Compose não encontrado${NC}"
    echo "Instale Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker OK (usando: $DOCKER_COMPOSE)${NC}\n"

# 2. Criar .env
echo -e "${YELLOW}[2/5]${NC} Criando arquivo .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ .env criado${NC}\n"
else
    echo -e "${YELLOW}⚠ .env já existe (não sobrescrito)${NC}\n"
fi

# 3. Iniciar Docker
echo -e "${YELLOW}[3/5]${NC} Iniciando serviços Docker..."
$DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.dev.yml up -d --build
echo -e "${GREEN}✓ Docker iniciado${NC}\n"

# 4. Aguardar backend estar pronto
echo -e "${YELLOW}[4/5]${NC} Aguardando backend ficar pronto..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -f http://localhost:8000/health 2>/dev/null; then
        echo -e "${GREEN}✓ Backend pronto${NC}\n"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "."
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}✗ Backend não respondeu no tempo limite${NC}"
    exit 1
fi

# 5. Resumo
echo -e "${GREEN}═════════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup Completo!${NC}"
echo -e "${GREEN}═════════════════════════════════════════${NC}\n"

echo "Serviços disponíveis:"
echo -e "  ${GREEN}Frontend:${NC}      http://localhost:3000"
echo -e "  ${GREEN}API:${NC}           http://localhost:8000"
echo -e "  ${GREEN}API Docs:${NC}      http://localhost:8000/docs"
echo -e "  ${GREEN}MinIO:${NC}         http://localhost:9001"
echo -e "  ${GREEN}Flower:${NC}        http://localhost:5555\n"

echo "Credenciais padrão:"
echo -e "  ${GREEN}Email:${NC}         admin@example.com"
echo -e "  ${GREEN}Senha:${NC}         admin123\n"

echo "Próximos passos:"
echo "  1. Abrir http://localhost:3000"
echo "  2. Fazer login"
echo "  3. Criar primeiro processo"
echo "  4. Fazer upload de PDF\n"

echo "Ver logs:"
echo "  docker-compose logs -f backend"
echo "  docker-compose logs -f celery_worker"
echo "  docker-compose logs -f frontend\n"

echo "Parar:"
echo "  docker-compose down\n"
