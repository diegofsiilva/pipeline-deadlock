# Extras

Programas que conferem as contas e medem o que o `ponderada-tato.md` afirma. Nenhum deles é necessário para rodar a questão A4.

| Arquivo | Para quê | Sustenta |
|---|---|---|
| `contas.py` | Deriva D1, D2 e N do nome e refaz as contas, com os limites de cada plataforma. | A1 |
| `pipeline.py` | Simula o pipeline, gera os diagramas e testa as 5.040 ordens das instruções. | A2 |
| `verificador.py` | Percorre todos os estados das threads e prova se há deadlock. | A4, A5 |
| `custos.c` | Repete a tabela "Quanto custa, medido" da aula. | A3 |
| `jitter.c` | Mede o atraso de uma tarefa de 100 Hz, para testar os "até 3 ms" do Linux. | A1, A3, B |
| `latencia_cache.c` | Mede o tempo de acesso em cada nível de memória. | A1 |
| `ritmo.c` | Roda as versões 2 e 3 a 100 Hz, com uma pausa opcional do motor. | A4 |
| `parceiro.c` | Mede a latência até o módulo do parceiro, em prioridade normal e mínima, e injeta falhas nele. | B |
| `medir_tudo.sh` | Repete todas as medições e grava em `resultados/`. Leva cerca de 20 minutos. | todas |
| `print_terminal.py` | Gera os prints a partir das saídas reais em `resultados/`. | A1, A4 |
| `graficos.py` | Gera os gráficos e diagramas. Precisa de matplotlib. | A1, A3, A4, A5 |

## Como usar

A partir de `ponderada/codigo`:

```bash
make extras
```

```bash
python3 extras/verificador.py
```

```bash
bash extras/medir_tudo.sh
```

## Sobre os prints

Os prints são a saída real do terminal, convertida em imagem por `print_terminal.py`. O texto cru de cada um está em `resultados/`, e os filtros usados aparecem no próprio comando do print.

## Limites das medições

Os números vêm de um notebook (i5-1345U, Linux 7.0, kernel com `PREEMPT_DYNAMIC`), não do hardware da pulseira. Eles valem para comparar arranjos e testar premissas. Antes de uma decisão de produção, seria preciso repetir tudo no SoC real.
