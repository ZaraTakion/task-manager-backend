# Task Manager API

API REST de gerenciamento de tarefas desenvolvida em **FastAPI**, com persistência
**SQLite**, validação via **Pydantic v2** e testes de regressão automatizados.

O projeto prioriza uma arquitetura pequena e verificável: sem ORM, filas ou
microsserviços desnecessários. Mantém compatibilidade com o CRUD original.

## Requisitos

- Python **3.10+**.
- Disco local persistente para o arquivo SQLite.

## Instalação

```bash
git clone https://github.com/ZaraTakion/task-manager-backend.git
cd task-manager-backend
python -m venv .venv
```

Ative o ambiente e instale as dependências:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

```bash
# Linux / macOS
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

O servidor de desenvolvimento fica em `http://127.0.0.1:8000` e a
documentação interativa em `http://127.0.0.1:8000/docs`.
O banco é criado automaticamente em `data/tasks.sqlite3`.

## Configuração

| Variável | Padrão | Função |
|---|---|---|
| `TASK_MANAGER_DB_PATH` | `data/tasks.sqlite3` | Caminho do arquivo SQLite |
| `TASK_MANAGER_API_KEY` | Ausente | Se definida, exige `X-API-Key` nas rotas de tarefas |

Veja `.env.example`. O projeto não carrega arquivos `.env` automaticamente:
configure variáveis no terminal ou no gerenciador de segredos da hospedagem.

**Importante:** por compatibilidade, as rotas de tarefas ficam **sem autenticação**
quando `TASK_MANAGER_API_KEY` não está definida. Para uso remoto, configure
uma chave longa e aleatória, utilize HTTPS e não exponha o serviço publicamente
sem controles apropriados. Uma string vazia na variável é recusada na inicialização.

Exemplo Linux/macOS (não reutilize a chave ilustrativa em produção):

```bash
export TASK_MANAGER_API_KEY='troque-por-um-segredo-longo-e-aleatorio'
uvicorn app.main:app
```

Chamadas autenticadas enviam `X-API-Key` como cabeçalho. O Swagger expõe
a opção **Authorize** para fornecer a chave. A rota `GET /` segue pública.

## API

| Método | Endpoint | Resposta |
|---|---|---|
| `GET` | `/` | `200` — saúde básica |
| `POST` | `/tasks` | `201` — cria tarefa |
| `GET` | `/tasks` | `200` — lista tarefas |
| `GET` | `/tasks/{task_id}` | `200` / `404` |
| `PATCH` | `/tasks/{task_id}` | `200` / `404` |
| `DELETE` | `/tasks/{task_id}` | `204` / `404` |

Exemplo de criação sem autenticação (configuração local padrão):

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Estudar FastAPI","completed":false}'
```

Campos da tarefa: `id` (inteiro), `title` (1–200 caracteres),
`completed` (booleano), `created_at` e `updated_at` (timestamps UTC).

Exemplo de atualização parcial:

```bash
curl -X PATCH http://127.0.0.1:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"completed":true}'
```

A API remove espaços em branco das extremidades do título, rejeita títulos
vazios, propriedades extras, `PATCH` vazio ou com valores nulos e IDs não
positivos. Entradas inválidas retornam **422**; tarefas inexistentes, **404**.
Quando a chave é exigida, ausência ou erro no cabeçalho retorna **401**.

### Filtros e paginação opcionais

`GET /tasks?completed=false&limit=20&offset=0`

- `completed`: `true` ou `false`.
- `limit`: entre **1** e **100** quando informado.
- `offset`: inteiro maior ou igual a zero (padrão: 0).
- Ordenação: `id` crescente, estável para paginação simples.

Sem parâmetros, `GET /tasks` mantém o comportamento anterior de retornar
a lista inteira. Para grandes volumes, prefira informar `limit`.

## Testes e qualidade

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m compileall -q app tests
ruff check app tests
```

O GitHub Actions verifica lint e executa testes em Python **3.10, 3.11, 3.12
e 3.13** a cada pull request para `main`. A suíte cobre CRUD, reinicialização
da aplicação, falhas de validação, isolamento de banco, autenticação opcional
e integridade transacional.

## Organização

```text
app/
  main.py       # Rotas FastAPI e factory create_app()
  schemas.py    # Regras Pydantic e contratos HTTP
  storage.py    # Repositório SQLite e transações
tests/
  test_api.py
  test_storage.py
docs/
  ARCHITECTURE.md
.github/workflows/
  tests.yml
```

O arquivo SQLite deve ficar em volume persistente. Para uso com várias réplicas
ou servidores, será necessário migrar para um banco compartilhado (por exemplo,
PostgreSQL); **não** compartilhe o arquivo SQLite por uma montagem de rede
entre servidores.

Veja [decisões de arquitetura e limites conhecidos](docs/ARCHITECTURE.md).
