# Task Manager API

API REST simples para criar, consultar, atualizar e excluir tarefas. O backend usa FastAPI e SQLite; as tarefas ficam em um arquivo de banco de dados em vez de uma lista em memória.

## Requisitos

- Python 3.10 ou superior

## Executar localmente

```bash
git clone https://github.com/ZaraTakion/task-manager-backend.git
cd task-manager-backend
python -m venv .venv
```

Ative o ambiente e instale as dependências:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

O SQLite é criado automaticamente em `data/tasks.sqlite3`. Para usar outro caminho, defina `TASK_MANAGER_DB_PATH` antes de iniciar o servidor. Por exemplo, em macOS/Linux:

```bash
TASK_MANAGER_DB_PATH=/caminho/persistente/tasks.sqlite3 uvicorn app.main:app --reload
```

Em hospedagens com disco efêmero, configure um volume persistente e aponte `TASK_MANAGER_DB_PATH` para ele. SQLite preserva dados entre reinícios enquanto o arquivo do banco permanecer no disco; réplicas simultâneas em vários servidores precisam de um banco compartilhado, como PostgreSQL.

## Endpoints

| Método | Rota | Ação |
|---|---|---|
| `GET` | `/` | Verifica se a API está respondendo |
| `POST` | `/tasks` | Cria uma tarefa (`title`, opcionalmente `completed`) |
| `GET` | `/tasks` | Lista tarefas |
| `GET` | `/tasks/{task_id}` | Consulta uma tarefa |
| `PATCH` | `/tasks/{task_id}` | Atualiza `title` e/ou `completed` |
| `DELETE` | `/tasks/{task_id}` | Exclui uma tarefa |

Documentação interativa: `http://127.0.0.1:8000/docs`.

Exemplo de criação:

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Estudar FastAPI","completed":false}'
```

## Testes

Os testes verificam o CRUD e recriam a aplicação sobre o mesmo arquivo SQLite para confirmar que os dados continuam disponíveis após uma reinicialização:

```bash
python -m unittest discover -s tests -v
```
