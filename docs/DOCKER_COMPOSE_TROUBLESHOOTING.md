# Docker Compose - Troubleshooting

## Problema: "Permission denied" ao rodar Docker

### Erro Completo
```
PermissionError(13, 'Permission denied')
Error while fetching server API version: ('Connection aborted.', PermissionError(13, 'Permission denied'))
```

### Causa

Seu usuário não tem permissão para acessar o socket do Docker.

### Solução (Linux/Mac)

```bash
# Adicionar seu usuário ao grupo docker
sudo usermod -aG docker $USER

# Aplicar novo grupo (sem logout)
newgrp docker

# Verificar se funciona
docker ps
```

Se `newgrp` não funcionar, faça logout e login novamente:
```bash
exit
# Faça login novamente e tente
docker ps
```

### Solução (Windows)

1. Verificar se Docker Desktop está rodando
2. Se usar WSL, reiniciar:
   ```bash
   wsl --shutdown
   ```
3. Abrir terminal como Administrador
4. Tentar novamente

### Solução Temporária

Use `sudo` para contornar (não recomendado):
```bash
sudo docker compose up --build
# ou
sudo ./scripts/init-dev.sh
```

---

## Problema: "docker-compose: command not found"

### Causa

Docker Compose foi integrado no Docker a partir da versão 1.20. Existem duas formas de usar:

- **Novo (recomendado):** `docker compose` (integrado ao Docker CLI)
- **Antigo (descontinuado):** `docker-compose` (comando standalone)

### Solução

#### 1. Verificar versão do Docker

```bash
docker --version
docker compose version
```

Se `docker compose version` funciona, você tem a versão nova. Use:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

#### 2. Se `docker compose` não funciona

Atualizar Docker:

**Windows (Docker Desktop):**
- Abrir Docker Desktop
- Settings → Check for updates
- Atualizar se disponível

**macOS (Docker Desktop):**
- Abrir Docker Desktop
- Menu → Check for updates
- Atualizar se disponível

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose separado (se necessário)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 3. Usar Script Automático

O script `./scripts/init-dev.sh` detecta automaticamente qual comando usar:

```bash
./scripts/init-dev.sh    # Linux/Mac
.\scripts\init-dev.bat   # Windows
```

### Verificação

```bash
# Verificar qual versão está disponível
docker compose version
# ou
docker-compose --version

# Ambos devem retornar versão 1.29 ou superior
```

## Problema: Portas em Conflito

Se portas (8000, 3000, 5432, etc) já estão em uso:

### Linux/Mac

```bash
# Encontrar processo usando porta 8000
lsof -i :8000

# Matar processo
kill -9 <PID>

# Ou mudar porta no .env
PORT_BACKEND=9000
PORT_FRONTEND=3001
```

### Windows

```powershell
# Encontrar processo usando porta 8000
netstat -ano | findstr :8000

# Matar processo
taskkill /PID <PID> /F

# Ou mudar porta no .env
```

## Problema: Permissões em Linux

Se erro de permissão ao rodar docker:

```bash
# Adicionar seu usuário ao grupo docker
sudo usermod -aG docker $USER

# Aplicar novo grupo (sem logout)
newgrp docker

# Ou fazer logout e login novamente
```

## Problema: Sem Espaço em Disco

Docker pode consumir muito espaço com imagens e volumes:

```bash
# Limpar imagens não usadas
docker image prune -a

# Limpar volumes não usados
docker volume prune

# Limpar tudo (perigoso!)
docker system prune -a --volumes
```

## Problema: Backend não Inicia

```bash
# Ver logs
docker compose logs backend

# Se erro de migrations
docker compose exec backend alembic upgrade head

# Reiniciar
docker compose restart backend
```

## Versão Recomendada

Para evitar problemas, use:

```bash
# Atualizar Docker
docker --version  # Deve ser 20.10 ou superior
docker compose version  # Deve ser v1.29 ou superior
```

### Instalação Fresca

**Windows/macOS:** Instalar [Docker Desktop](https://www.docker.com/products/docker-desktop)

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Verificar
docker --version
docker compose version
```
