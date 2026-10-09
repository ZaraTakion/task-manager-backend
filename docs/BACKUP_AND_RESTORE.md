# Backup e restauração do SQLite

Este projeto usa um arquivo SQLite local, não um serviço gerenciado. Sem backup externo,
a perda do disco implica perda das tarefas. Use apenas dados de demonstração nos testes.

## Backup sem interromper o servidor

A ferramenta usa a **API de backup nativa do SQLite**, que produz um snapshot
transacionalmente consistente mesmo quando há outras conexões escrevendo no banco.
Ela verifica a integridade da cópia e **se recusa a sobrescrever backups existentes**.
O destino recebe um nome novo em cada execução.

Execute na raiz do repositório:

```bash
python scripts/backup_sqlite.py --destination backups/tasks-2026-10-09.sqlite3
```

O argumento `--source` é opcional. Sem ele, é usada a variável `TASK_MANAGER_DB_PATH`
(se definida) ou `data/tasks.sqlite3` do projeto:

```bash
python scripts/backup_sqlite.py --source data/tasks.sqlite3 --destination backups/tasks-manual.sqlite3
```

**Segurança:** os arquivos `.sqlite3`, `.db` e a pasta `backups/` são ignorados
pelo Git. Não publique cópias de dados reais, mesmo em repositórios privados.
Backups são criados com permissões restritas pelo sistema operacional local;
armazene uma cópia protegida fora do mesmo disco, se os dados forem importantes.

## Restauração

1. **Pare** o processo `uvicorn` e quaisquer outros processos conectados ao banco.
2. Guarde uma cópia de segurança do banco atual com nome diferente.
3. Confirme a integridade do backup antes de usar:
   ```bash
   python -c "import sqlite3; c=sqlite3.connect('backups/tasks-manual.sqlite3'); print(c.execute('PRAGMA integrity_check').fetchone()[0]); c.close()"
   ```
   O resultado esperado é `ok`.
4. Copie o arquivo de backup para o caminho definido em `TASK_MANAGER_DB_PATH`
   (ou `data/tasks.sqlite3` por padrão), substituindo o banco **somente com o servidor parado**.
5. Inicie novamente a aplicação e verifique `GET /tasks`. Em caso de anomalia,
   interrompa o servidor e restaure a cópia anterior.

Exemplo Linux/macOS quando o servidor estiver parado:

```bash
cp backups/tasks-manual.sqlite3 data/tasks.sqlite3
```

No PowerShell, com o servidor parado:

```powershell
Copy-Item backups/tasks-manual.sqlite3 data/tasks.sqlite3 -Force
```

Não copie manualmente um banco SQLite aberto para fazer um backup: podem existir
transações ainda não consolidadas e, caso seja usado WAL no futuro, arquivos
auxiliares. Para **criar** backups, prefira sempre o script.

## Limites operacionais

- O backup local não substitui armazenamento externo nem testes de recuperação.
- O script não agenda backups, não cifra os arquivos e não cria recursos pagos.
- Em múltiplas réplicas, o SQLite não deve ser compartilhado por montagem de rede.
- A restauração é um procedimento **offline**, diferente do backup online.
- Os testes usam arquivos temporários e verificam preservação, não sobrescrita,
  restauração e falha segura diante de banco corrompido.

Para verificar: `python -m unittest discover -s tests -v`.
