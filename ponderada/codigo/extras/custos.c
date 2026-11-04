/*
 * custos.c
 *
 * Reproduz, nesta máquina, a tabela "Quanto custa, medido" da aula de
 * processos e threads: criar thread, criar processo e trocar de contexto entre
 * threads e entre processos. Serve para a questão A3 discutir custo com número.
 *
 * Mesmo método da aula: mediana de 5 execuções, tudo no mesmo núcleo. Criar
 * inclui encerrar e esperar; trocar inclui o custo do pipe.
 *
 * Uso: taskset -c 2 ./custos
 */

#include <pthread.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define EXECUCOES 5

extern char **environ;

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
 * thread_vazia: corpo das threads criadas na medição.
 *
 * Parâmetros:
 *   arg: não usado.
 * Retorno: NULL.
 * Funcionamento: termina imediatamente.
 */
static void *thread_vazia(void *arg)
{
    return arg;
}

/*
 * cria_threads: mede pthread_create seguido de pthread_join.
 *
 * Parâmetros:
 *   n: quantas repetições.
 * Retorno: microssegundos por operação.
 * Funcionamento: cria e espera uma thread por vez.
 */
static double cria_threads(int n)
{
    double inicio = agora();

    for (int i = 0; i < n; i++) {
        pthread_t t;
        pthread_create(&t, NULL, thread_vazia, NULL);
        pthread_join(t, NULL);
    }
    return (agora() - inicio) / n * 1e6;
}

/*
 * cria_processos: mede fork seguido de waitpid.
 *
 * Parâmetros:
 *   n: quantas repetições.
 * Retorno: microssegundos por operação.
 * Funcionamento: o filho termina na hora, sem trocar de programa.
 */
static double cria_processos(int n)
{
    double inicio = agora();

    for (int i = 0; i < n; i++) {
        pid_t pid = fork();
        if (pid == 0)
            _exit(0);
        waitpid(pid, NULL, 0);
    }
    return (agora() - inicio) / n * 1e6;
}

/*
 * cria_programas: mede posix_spawn de outro programa seguido de waitpid.
 *
 * Parâmetros:
 *   n: quantas repetições.
 * Retorno: microssegundos por operação.
 * Funcionamento: roda /bin/true, que termina na hora.
 */
static double cria_programas(int n)
{
    char *args[] = {"true", NULL};
    double inicio = agora();

    for (int i = 0; i < n; i++) {
        pid_t pid;
        posix_spawn(&pid, "/bin/true", NULL, NULL, args, environ);
        waitpid(pid, NULL, 0);
    }
    return (agora() - inicio) / n * 1e6;
}

/* Os dois pipes do pingue-pongue e o número de idas e voltas. */
struct pingue {
    int ida[2];
    int volta[2];
    int n;
};

/*
 * responde: lado que devolve cada byte recebido no pingue-pongue.
 *
 * Parâmetros:
 *   arg: ponteiro para struct pingue.
 * Retorno: NULL.
 * Funcionamento: bloqueia no pipe de ida e escreve no pipe de volta.
 */
static void *responde(void *arg)
{
    struct pingue *p = arg;
    char c;

    for (int i = 0; i < p->n; i++) {
        if (read(p->ida[0], &c, 1) != 1 || write(p->volta[1], &c, 1) != 1)
            break;
    }
    return NULL;
}

/*
 * dispara: lado que inicia cada ida e volta e mede o tempo.
 *
 * Parâmetros:
 *   p: pipes do pingue-pongue.
 * Retorno: microssegundos por troca de contexto.
 * Funcionamento: cada ida e volta força duas trocas, porque as duas pontas
 * dividem o mesmo núcleo.
 */
static double dispara(struct pingue *p)
{
    char c = 'x';
    double inicio = agora();

    for (int i = 0; i < p->n; i++) {
        if (write(p->ida[1], &c, 1) != 1 || read(p->volta[0], &c, 1) != 1)
            break;
    }
    return (agora() - inicio) / (2.0 * p->n) * 1e6;
}

/*
 * troca_threads: mede a troca de contexto entre duas threads.
 *
 * Parâmetros:
 *   n: quantas idas e voltas.
 * Retorno: microssegundos por troca.
 * Funcionamento: a outra ponta do pingue-pongue é uma thread.
 */
static double troca_threads(int n)
{
    struct pingue p = {.n = n};
    pthread_t t;

    if (pipe(p.ida) != 0 || pipe(p.volta) != 0)
        exit(1);
    pthread_create(&t, NULL, responde, &p);
    double resultado = dispara(&p);
    pthread_join(t, NULL);
    return resultado;
}

/*
 * troca_processos: mede a troca de contexto entre dois processos.
 *
 * Parâmetros:
 *   n: quantas idas e voltas.
 * Retorno: microssegundos por troca.
 * Funcionamento: a outra ponta do pingue-pongue é um processo filho.
 */
static double troca_processos(int n)
{
    struct pingue p = {.n = n};

    if (pipe(p.ida) != 0 || pipe(p.volta) != 0)
        exit(1);
    pid_t pid = fork();
    if (pid == 0) {
        responde(&p);
        _exit(0);
    }
    double resultado = dispara(&p);
    waitpid(pid, NULL, 0);
    return resultado;
}

/*
 * compara: critério de ordenação para o qsort.
 *
 * Parâmetros:
 *   a, b: ponteiros para double.
 * Retorno: negativo, zero ou positivo, como o qsort espera.
 * Funcionamento: compara os dois valores.
 */
static int compara(const void *a, const void *b)
{
    double x = *(const double *)a, y = *(const double *)b;

    return (x > y) - (x < y);
}

/*
 * mediana: roda uma medição EXECUCOES vezes.
 *
 * Parâmetros:
 *   rotulo: descrição impressa na linha.
 *   medicao: função que mede.
 *   n: repetições por execução.
 * Retorno: nenhum.
 * Funcionamento: ordena os resultados e imprime o valor do meio.
 */
static void mediana(const char *rotulo, double (*medicao)(int), int n)
{
    double valores[EXECUCOES];

    for (int i = 0; i < EXECUCOES; i++)
        valores[i] = medicao(n);
    qsort(valores, EXECUCOES, sizeof valores[0], compara);
    printf("%10.2f us  %s\n", valores[EXECUCOES / 2], rotulo);
}

/*
 * main: executa todas as medições.
 *
 * Parâmetros: nenhum.
 * Retorno: 0.
 * Funcionamento: deve rodar preso a um núcleo com taskset.
 */
int main(void)
{
    mediana("criar thread (pthread_create)", cria_threads, 20000);
    mediana("criar processo (fork)", cria_processos, 5000);
    mediana("criar processo com outro programa (spawn)", cria_programas, 1000);
    mediana("trocar entre threads (pipe, mesmo núcleo)", troca_threads, 200000);
    mediana("trocar entre processos (pipe, mesmo núcleo)", troca_processos, 200000);
    return 0;
}
