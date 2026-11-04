/*
 * latencia_cache.c
 *
 * Mede o gargalo de Von Neumann nesta máquina. Percorre uma lista encadeada
 * em ordem aleatória, com tamanhos crescentes. Cada passo depende do anterior,
 * então o processador não consegue adiantar leituras nem prever o próximo
 * endereço. Quando a lista deixa de caber em um nível de cache, o tempo de
 * acesso sobe um degrau.
 *
 * Uso: taskset -c 2 ./latencia_cache
 */

#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>

#define LINHA_BYTES 64
#define PASSOS 40000000L

/* Uma posição da lista, com o tamanho de uma linha de cache. */
struct no {
    struct no *proximo;
    char preenchimento[LINHA_BYTES - sizeof(struct no *)];
};

static struct no *volatile fim_da_lista;

/*
 * agora: lê o relógio monotônico.
 *
 * Parâmetros: nenhum.
 * Retorno: tempo em segundos, com origem arbitrária.
 * Funcionamento: o relógio monotônico não sofre ajustes de horário.
 */
static double agora(void)
{
    struct timespec t;

    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

/*
 * monta_lista: liga as posições em um único ciclo aleatório.
 *
 * Parâmetros:
 *   nos: área já alocada.
 *   n: número de posições.
 * Retorno: nenhum.
 * Funcionamento: embaralha os índices com Fisher-Yates e liga cada um ao
 * seguinte, o que garante um ciclo que passa por todas as posições.
 */
static void monta_lista(struct no *nos, size_t n)
{
    size_t *ordem = malloc(n * sizeof *ordem);

    for (size_t i = 0; i < n; i++)
        ordem[i] = i;
    for (size_t i = n - 1; i > 0; i--) {
        size_t j = (size_t)rand() % (i + 1);
        size_t t = ordem[i];
        ordem[i] = ordem[j];
        ordem[j] = t;
    }
    for (size_t i = 0; i < n; i++)
        nos[ordem[i]].proximo = &nos[ordem[(i + 1) % n]];
    free(ordem);
}

/*
 * mede: calcula o tempo médio de um acesso em uma lista de um dado tamanho.
 *
 * Parâmetros:
 *   bytes: tamanho da lista.
 * Retorno: nanossegundos por acesso.
 * Funcionamento: percorre a lista uma vez para aquecer a cache e depois mede
 * PASSOS acessos. Pede páginas enormes para reduzir o efeito das faltas de TLB.
 * Guardar o ponteiro final em fim_da_lista impede o compilador de apagar o laço
 * sem colocar nenhum acesso extra à memória dentro dele.
 */
static double mede(size_t bytes)
{
    size_t n = bytes / sizeof(struct no);
    struct no *nos = mmap(NULL, bytes, PROT_READ | PROT_WRITE,
                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);

    madvise(nos, bytes, MADV_HUGEPAGE);
    monta_lista(nos, n);

    struct no *p = nos;
    for (size_t i = 0; i < n; i++)
        p = p->proximo;

    double inicio = agora();
    for (long i = 0; i < PASSOS; i++)
        p = p->proximo;
    double duracao = agora() - inicio;

    fim_da_lista = p;
    munmap(nos, bytes);
    return duracao / PASSOS * 1e9;
}

/*
 * main: varre os tamanhos de 8 KiB a 256 MiB.
 *
 * Parâmetros: nenhum.
 * Retorno: 0.
 * Funcionamento: dobra o tamanho a cada passo, com um ponto intermediário, e
 * imprime KiB e nanossegundos separados por tabulação.
 */
int main(void)
{
    srand(2026);
    for (size_t base = 8 * 1024; base <= 256 * 1024 * 1024; base *= 2) {
        printf("%zu\t%.2f\n", base / 1024, mede(base));
        fflush(stdout);
        if (base < 256 * 1024 * 1024) {
            printf("%zu\t%.2f\n", base * 3 / 2 / 1024, mede(base * 3 / 2));
            fflush(stdout);
        }
    }
    return 0;
}
