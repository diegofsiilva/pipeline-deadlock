#!/usr/bin/env bash
#
# medir_tudo.sh
#
# Repete todas as medições citadas no ponderada-tato.md e grava as saídas em
# resultados/. Leva cerca de 20 minutos. Rode com a máquina parada: os primeiros
# testes medem tempo e são sensíveis a outros programas.
#
# As 9 execuções da tabela da questão A4 são as primeiras que saírem, sem
# seleção. Os testes presos a um núcleo usam a CPU 2, um núcleo de desempenho.
#
# Uso, a partir de ponderada/codigo: bash extras/medir_tudo.sh

set -u
cd "$(dirname "$0")/.."

NUCLEO=2
SAIDA=resultados

# jitter: mede a tarefa de 100 Hz por 30 s com um concorrente opcional.
# Parâmetros: $1, rótulo da linha; $2, política do concorrente no mesmo núcleo
# (nenhum, normal ou idle).
# Retorno: nada; acrescenta o resultado a resultados/jitter.txt.
# Funcionamento: cria o concorrente preso ao mesmo núcleo, mede e o encerra.
jitter() {
    local concorrente=""
    case "$2" in
        normal) taskset -c "$NUCLEO" yes > /dev/null & concorrente=$! ;;
        idle) taskset -c "$NUCLEO" chrt -i 0 yes > /dev/null & concorrente=$! ;;
    esac
    sleep 0.5
    { echo "--- $1"; taskset -c "$NUCLEO" extras/bin/jitter 30; } >> "$SAIDA/jitter.txt"
    if [ -n "$concorrente" ]; then
        kill "$concorrente"
        wait "$concorrente" 2> /dev/null
    fi
}

# jitter_todos_ocupados: mede a tarefa com um concorrente em cada CPU.
# Parâmetros: nenhum.
# Retorno: nada; acrescenta o resultado a resultados/jitter.txt.
# Funcionamento: cria um processo yes por CPU e mede sem prender a tarefa.
jitter_todos_ocupados() {
    local pids=()
    for cpu in $(seq 0 $(($(nproc) - 1))); do
        taskset -c "$cpu" yes > /dev/null &
        pids+=($!)
    done
    sleep 0.5
    { echo "--- todos os núcleos ocupados"; extras/bin/jitter 30; } >> "$SAIDA/jitter.txt"
    kill "${pids[@]}"
    wait "${pids[@]}" 2> /dev/null
}

# campanha: repete um comando e grava uma linha por execução.
# Parâmetros: $1, cenário; $2, repetições; demais, o comando.
# Retorno: nada; acrescenta linhas a resultados/campanha.tsv.
# Funcionamento: extrai os campos do relatório comum das versões.
campanha() {
    local cenario=$1 repeticoes=$2
    shift 2
    for _ in $(seq "$repeticoes"); do
        "$@" | awk -v c="$cenario" '
            /produzidas/ { p = $3 } /consumidas/ { n = $3 } /perdidas/ { l = $3 }
            /duplicadas/ { d = $3 } /travou/ { t = $3 } /tempo/ { s = $3 }
            END { print c "\t" p "\t" n "\t" l "\t" d "\t" t "\t" s }' >> "$SAIDA/campanha.tsv"
    done
}

# sem_mutex: testa a versão 2 sem as operações no mutex.
# Parâmetros: nenhum.
# Retorno: nada; grava o resumo em resultados/sem_mutex.txt.
# Funcionamento: gera a cópia sem o mutex em extras/bin, roda 200 vezes e passa
# uma vez no ThreadSanitizer.
sem_mutex() {
    grep -vE 'sem_(wait|post)\(&mutex\)' versao2.c > extras/bin/sem_mutex.c
    gcc -O2 -g -pthread -I. -o extras/bin/sem_mutex extras/bin/sem_mutex.c
    gcc -O1 -g -pthread -fsanitize=thread -I. -o extras/bin/sem_mutex_tsan extras/bin/sem_mutex.c
    {
        echo "versão 2 sem mutex, 200 execuções"
        for _ in $(seq 200); do
            extras/bin/sem_mutex
        done | awk '
            /perdidas/ { l += $3 } /duplicadas/ { d += $3 } /travou/ { if ($3 == "sim") t++ }
            END { printf "perdidas: %d\nduplicadas: %d\ntravaram: %d\n", l, d, t }'
        echo "avisos do ThreadSanitizer: $(TSAN_OPTIONS=report_thread_leaks=0 \
            extras/bin/sem_mutex_tsan 2>&1 | grep -c 'WARNING: ThreadSanitizer')"
    } > "$SAIDA/sem_mutex.txt"
}

make -s versao1 versao2 versao3 versao1_tsan versao2_tsan extras
rm -f "$SAIDA"/jitter.txt "$SAIDA"/campanha.tsv

{ lscpu | grep -E '^Nome do modelo|^cache de'; echo; lscpu -C; } > "$SAIDA/lscpu.txt"

echo "custos"
taskset -c "$NUCLEO" extras/bin/custos > "$SAIDA/custos.txt"

echo "jitter"
jitter "ociosa" nenhum
jitter "concorrente normal no mesmo núcleo" normal
jitter "concorrente SCHED_IDLE no mesmo núcleo" idle
jitter_todos_ocupados

echo "latência de cache"
taskset -c "$NUCLEO" extras/bin/latencia_cache > "$SAIDA/latencia_cache.tsv"

echo "parceiro"
taskset -c "$NUCLEO" extras/bin/parceiro latencia > "$SAIDA/parceiro_latencia.txt"
extras/bin/parceiro falhas > "$SAIDA/parceiro_falhas.txt" 2>&1

echo "execuções oficiais"
for versao in 1 2 3; do
    for rodada in 1 2 3; do
        echo "--- versão $versao, execução $rodada"
        make --no-print-directory "v$versao"
    done
done > "$SAIDA/execucoes.txt"

echo "ferramentas"
make --no-print-directory tsan1 > "$SAIDA/tsan_v1.txt" 2>&1
make --no-print-directory tsan2 > "$SAIDA/tsan_v2.txt" 2>&1
sem_mutex
gdb -q -batch -ex 'set pagination off' -ex 'set debuginfod enabled off' \
    -ex 'break relatorio' -ex run -ex 'thread apply all bt' ./versao3 > "$SAIDA/gdb_v3.txt" 2>&1

echo "ritmo real e campanha"
for caso in "3 0" "3 20" "3 50" "2 50"; do
    # shellcheck disable=SC2086
    extras/bin/ritmo $caso > "$SAIDA/ritmo_${caso/ /_}.txt" &
done
campanha "v1 vários núcleos" 200 ./versao1
campanha "v2 vários núcleos" 200 ./versao2
campanha "v3 vários núcleos" 100 ./versao3
campanha "v2 um núcleo" 20 taskset -c "$NUCLEO" ./versao2
campanha "v3 um núcleo" 20 taskset -c "$NUCLEO" ./versao3
campanha "v1 um núcleo" 20 taskset -c "$NUCLEO" ./versao1
wait
echo "fim"
