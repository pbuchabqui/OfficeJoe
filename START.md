# 🚀 OfficeJoe - One Click Start

## 🎯 Iniciar Tudo com Um Click

```bash
python run.py
```

**Ou no Linux/Mac:**
```bash
./run.sh
```

## ✅ O que acontece?

1. ✓ Verifica Docker
2. ✓ Inicia Docker Compose (backend, banco, cache, etc)
3. ✓ Aguarda backend ficar online
4. ✓ Inicia Streamlit automaticamente

## 🎨 Depois de rodar

Abra seu navegador em:

| Serviço | URL | Uso |
|---------|-----|-----|
| **Streamlit** | http://localhost:8501 | 💻 Interface principal |
| **API Docs** | http://localhost:8000/docs | 📚 Documentação da API |
| **MinIO Console** | http://localhost:9001 | 💾 Armazenamento de arquivos |
| **Flower** | http://localhost:5555 | 🌼 Monitoramento de tarefas |

## 🔐 Login

```
Email:    admin@example.com
Senha:    admin123
```

## ⏹️ Parar

Pressione `Ctrl+C` no terminal

---

## 📝 Primeira Vez?

```bash
# 1. Instalar dependências (uma vez)
pip install streamlit requests

# 2. Rodar
python run.py
```

Pronto! 🎉
