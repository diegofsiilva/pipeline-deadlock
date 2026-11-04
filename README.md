# pipeline-deadlock

**Diego Figueiredo Silva**

Ponderada de Computação CC08: arquitetura, pipeline, threads, semáforos e deadlock aplicados à pulseira sensorial da Tato.

O trabalho está em [ponderada/ponderada-tato.md](ponderada/ponderada-tato.md).

## Como rodar a questão A4

Precisa de Linux (ou WSL), `gcc` e `make`. Cada versão compila e roda com um único comando, a partir da raiz do repositório:

```bash
make -C ponderada/codigo v1
```

```bash
make -C ponderada/codigo v2
```

```bash
make -C ponderada/codigo v3
```

| Comando | Versão | O que esperar |
|---|---|---|
| `v1` | Sem sincronização | Perde e duplica amostras, e às vezes trava. Muda a cada execução. |
| `v2` | Com semáforos | Sempre 20.000 consumidas, 0 perdidas, 0 duplicadas. |
| `v3` | Ordem trocada | Deadlock. O vigia encerra depois de 1 s sem consumo. |

O macOS não tem `sem_init`, então lá é preciso usar um contêiner ou uma máquina Linux.

## Organização

```text
ponderada/
├── ponderada-tato.md    Parte A e Parte B
├── img/                 prints, gráficos e diagramas
└── codigo/
    ├── versao1.c, versao2.c, versao3.c, comum.h, Makefile    questão A4
    ├── resultados/      saídas cruas de todas as medições
    └── extras/          o que confere as contas e mede o que o texto afirma
```

O [README de extras](ponderada/codigo/extras/README.md) explica cada programa e como repetir as medições.
