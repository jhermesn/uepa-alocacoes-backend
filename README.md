## AlocacoesUEPA - Backend (FastAPI)

API para gestão de salas e reservas integrada ao Google Calendar.

### 🚀 Começando

#### Pré-requisitos
- Docker e Docker Compose instalados.

#### Executar o ambiente
```bash
# Iniciar os serviços em background
docker compose up -d

# Visualizar logs em tempo real
docker compose logs -f app

# Parar os serviços
docker compose down
```

### 🧹 Limpeza e Reset de Ambiente (Clean Slate)

Se você precisar reiniciar o banco de dados do zero (limpando volumes e reconstruindo imagens):

```bash
# Baixar o ambiente removendo volumes e imagens locais
docker compose down -v --rmi local

# Subir novamente forçando o build
docker compose up --build -d
```
*Este processo executará automaticamente as migrações e o seed inicial de dados (usuários e salas).*

---

### ⚙️ Variáveis de Ambiente

A aplicação utiliza variáveis de ambiente para configuração. Você deve criar um arquivo `.env` na raiz do projeto baseado nos exemplos fornecidos:

- **Desenvolvimento**: Use [.env.example](.env.example) como base.

#### Principais Variáveis:
- `DATABASE_URL`: URL de conexão com o banco de dados. No Docker (dev), ela é configurada automaticamente.
- `JWT_SECRET`: Chave secreta para geração de tokens JWT.
- `GOOGLE_CLIENT_ID` / `SECRET`: Credenciais para integração com Google Calendar.
- `GOOGLE_REDIRECT_URI`: URL de callback para o OAuth do Google.

---

### 🧪 Testes

Os testes automatizados são executados dentro do container da aplicação:

```bash
docker compose exec app env PYTHONPATH=. pytest
```

---

### 📖 Documentação da API

A documentação detalhada e interativa está disponível no seguinte endpoint (com o ambiente rodando):

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)

#### Autenticação Rápida

A maioria das rotas exige um Token JWT (Bearer).

1.  **Login**:
    ```bash
    curl -X POST http://localhost:8000/auth/login \
         -H "Content-Type: application/json" \
         -d '{"username": "admin", "password": "admin456"}'
    ```
2.  **Uso do Token**:
    Inclua o reader `Authorization: Bearer <seu_token>` nas suas requisições.

#### Credenciais Padrão (Seed)
- **Usuário**: `admin@uepa.br` (username: `admin`)
- **Senha**: `admin456`

---

### 🛠️ Desenvolvimento Local (Sem Docker)

Se preferir rodar fora do Docker, você precisará de um banco PostgreSQL e das variáveis de ambiente configuradas no `.env`.

1.  Crie um ambiente virtual: `python -m venv venv`
2.  Ative: `source venv/bin/activate`
3.  Instale: `pip install -r requirements.txt`
4.  Execute: `./scripts/init.sh` (ajuste o host/port no script se necessário)

---

### 📂 Estrutura do Projeto

- `app/`: Código fonte da aplicação (routers, models, schemas, services).
- `alembic/`: Migrações do banco de dados.
- `scripts/`: Scripts de utilidade (init, seed, etc).
- `tests/`: Suíte de testes automatizados.
