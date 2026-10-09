# Estudo de caso — Task Manager API

## Problema e escopo
Construir uma API pequena e reproduzível de tarefas, com persistência real entre reinicializações e contratos HTTP verificáveis. O escopo inclui CRUD, filtros/paginação opt-in e uma barreira de API key opcional para cenários controlados.

## Arquitetura
```text
Cliente HTTP
    |
FastAPI (app/main.py)  --- Pydantic (app/schemas.py)
    |
TaskStore (app/storage.py)
    |
SQLite local (data/tasks.sqlite3)
```

- `create_app(database_path)` permite instâncias independentes e isolamento entre bancos de testes.
- `TaskCreate` e `TaskUpdate` rejeitam propriedades inesperadas, campos nulos, títulos inválidos e PATCH vazio.
- `TaskStore` executa SQL parametrizado, conexões curtas e transações nas escritas; a lista ordena por ID, com filtro `completed`, `limit` e `offset` opcionais.
- `TASK_MANAGER_API_KEY` usa cabeçalho `X-API-Key` e comparação resistente a diferenças de tempo. Sem a variável, a API mantém compatibilidade com acesso público local.

## Contratos e testes
- `POST /tasks`: 201; `GET /tasks`: 200; `GET/PATCH /tasks/{id}`: 200/404; `DELETE /tasks/{id}`: 204/404.
- Falhas de validação retornam 422. O contrato JSON da tarefa mantém `id`, `title`, `completed`, `created_at` e `updated_at`.
- [Testes HTTP](../tests/test_api.py): criação, leitura, atualização, exclusão, erros, autenticação, filtros e persistência após recriar a aplicação.
- [Testes de persistência](../tests/test_storage.py): constraints, rollback de escrita inválida, exclusão e recriação do repositório.
- [GitHub Actions](../.github/workflows/tests.yml): Python 3.10–3.13, Ruff, compileall e relatório de cobertura `coverage.xml` em revisão pelo [PR #2](https://github.com/ZaraTakion/task-manager-backend/pull/2).

## Trade-offs e riscos
SQLite reduz o custo de execução local, mas não serve para instâncias independentes com banco em filesystem remoto compartilhado. A ausência de autenticação por padrão é preservada por compatibilidade; para uma implantação remota, configurar chave de API forte e HTTPS não substitui rate limiting ou autenticação individual. Não alegamos desempenho, disponibilidade pública nem métricas não medidas.

## Reproduzir
```bash
python -m pip install -r requirements-dev.txt
coverage run --source=app -m unittest discover -s tests -v
coverage report -m
ruff check app tests
uvicorn app.main:app --reload
```

**Estado:** alterações sob revisão no PR #2. A integração na `main` e a confirmação da nova rodada CI precisam ser verificadas antes de descrever esta revisão como release.
