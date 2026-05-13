#!/usr/bin/env python3
"""
🚀 OfficeJoe One-Click Launcher
Inicia tudo com um comando: python run.py
"""

import subprocess
import time
import requests
import sys
import os
from pathlib import Path

# Cores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    """Exibe header do app"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════╗")
    print("║     🚀 OfficeJoe One-Click Launcher 🚀    ║")
    print("╚════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

def print_step(step_num, message):
    """Exibe um passo"""
    print(f"{Colors.BOLD}{Colors.BLUE}[{step_num}]{Colors.END} {message}")

def print_success(message):
    """Exibe mensagem de sucesso"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message):
    """Exibe mensagem de erro"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_warning(message):
    """Exibe mensagem de aviso"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def check_docker():
    """Verifica se Docker está instalado e rodando"""
    print_step("1", "Verificando Docker...")
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print_success(result.stdout.strip())
            return True
        else:
            print_error("Docker não está instalado")
            return False
    except Exception as e:
        print_error(f"Docker não encontrado: {e}")
        return False

def start_docker_compose():
    """Inicia Docker Compose"""
    print_step("2", "Iniciando Docker Compose...")
    print(f"{Colors.YELLOW}⏳ Aguarde (pode levar alguns minutos na primeira vez)...{Colors.END}\n")
    
    try:
        # Inicia os containers em background
        subprocess.Popen(
            ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.dev.yml", "up"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print_success("Docker Compose iniciado em background")
        return True
    except Exception as e:
        print_error(f"Erro ao iniciar Docker Compose: {e}")
        return False

def wait_for_backend(max_attempts=60, timeout=2):
    """Aguarda backend ficar online"""
    print_step("3", "Aguardando backend ficar online...")
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(
                "http://localhost:8000/docs",
                timeout=timeout
            )
            if response.status_code == 200:
                print_success("Backend está online em http://localhost:8000")
                return True
        except:
            pass
        
        # Mostrar progresso
        print(f"  {attempt + 1}/{max_attempts} tentativas...", end="\r")
        time.sleep(1)
    
    print_error("Backend não ficou online a tempo")
    print_warning("Você pode precisar verificar os logs com: docker compose logs backend")
    return False

def start_streamlit():
    """Inicia Streamlit"""
    print_step("4", "Iniciando Streamlit...")
    print(f"\n{Colors.BOLD}{Colors.GREEN}")
    print("╔════════════════════════════════════════════╗")
    print("║        🎉 Tudo pronto para usar! 🎉      ║")
    print("╚════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    print(f"{Colors.BOLD}URLs:{Colors.END}")
    print(f"  🎨 Streamlit:     http://localhost:8501")
    print(f"  📚 API Docs:      http://localhost:8000/docs")
    print(f"  💾 MinIO:         http://localhost:9001")
    print(f"  🌼 Flower:        http://localhost:5555\n")
    
    print(f"{Colors.BOLD}Credenciais:{Colors.END}")
    print(f"  Email:    admin@example.com")
    print(f"  Senha:    admin123\n")
    
    print(f"{Colors.YELLOW}Iniciando Streamlit...{Colors.END}\n")
    
    try:
        subprocess.run(
            ["streamlit", "run", "app_streamlit.py"],
            check=False
        )
    except Exception as e:
        print_error(f"Erro ao iniciar Streamlit: {e}")
        print_warning("Instale com: pip install streamlit requests")
        return False
    
    return True

def main():
    """Função principal"""
    print_header()
    
    # Verificar Docker
    if not check_docker():
        print_error("Por favor, instale Docker e tente novamente")
        sys.exit(1)
    
    # Iniciar Docker Compose
    if not start_docker_compose():
        print_error("Falha ao iniciar Docker Compose")
        sys.exit(1)
    
    # Aguardar backend
    if not wait_for_backend():
        print_warning("Backend pode estar demorando para iniciar...")
        print_warning("Aguarde alguns minutos e tente novamente")
        time.sleep(10)
    
    # Iniciar Streamlit
    start_streamlit()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⏹️  Aplicação interrompida pelo usuário{Colors.END}")
        sys.exit(0)
