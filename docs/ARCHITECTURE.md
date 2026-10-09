# Arquitetura e decisões técnicas

## Componentes

- `app/main.py`: fábrica FastAPI, endpoints e dependência de autenticação opcional.
- `app/schemas.py`: contratos de entrada/saída e validações Pydantic v2.
- `app/storage.py`: operações SQL parametrizadas, transações curtas e tipos dos registros.
- `tests/`: testes de contrato HTTP e regressão da persistência SQLite.

`create_app(database_path)` permite criar instâncias isoladas sem afetar o banco padrão.
O arquivo SQLite é inicializado no momento em que a aplicação é construída.

## Compatibilidade

Mantidos os verbos, rotas, status 201/204 e campos do CRUD. `GET /tasks` continua
listando todos os registros sem parâmetros para não quebrar clientes existentes.
Novos parâmetros opcionais: `completed`, `limit` (1 a 100) e `offset` (a partir de 0).

O título é normalizado com `strip()`, não pode ser vazio nem ultrapassar 200
caracteres antes da normalização. Objetos com propriedades adicionais são rejeitados.
PATCH exige ao menos um campo e não aceita valores nulos.

## Persistência

Uma conexão SQLite por operação, com timeout de 10 segundos e transações explícitas
nas escritas. A tabela tem restrições CHECK para título e status; existe índice para
consultas por `completed` e `id`. O banco existente não é recriado nem apagado.

SQLite é adequado para um serviço local ou pequena instância com disco persistente.
Não é apropriado compartilhar o arquivo por rede entre réplicas independentes.
Migração para PostgreSQL só se justifica quando o uso exigir múltiplas instâncias
ou maior concorrência.

## Segurança e limitações

Sem `TASK_MANAGER_API_KEY`, a API mantém o comportamento original: as rotas
de tarefas estão públicas. Com a variável configurada, todas as rotas `/tasks`
exigem o cabeçalho `X-API-Key` (HTTP 401 se ausente/incorreto), com comparação
em tempo constante. `GET /`, OpenAPI e Swagger permanecem acessíveis.

A chave única não implementa contas, permissões por usuário, rotação automática,
limites de taxa, nem auditoria individual. Não publicar uma instância de produção
sem HTTPS, armazenamento seguro da chave e controles de acesso adequados.
Nenhuma configuração CORS permissiva foi adicionada.

## Evoluções deliberadamente adiadas

Paginação sem limite padrão seria uma mudança incompatível; o parâmetro é opt-in.
Autenticação multiusuário, PostgreSQL, ORM, migrations e filas não foram introduzidos
porque acrescentariam custo desproporcional para o CRUD atual.
