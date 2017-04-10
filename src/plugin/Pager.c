#include <pthread.h>
#include <signal.h>
#include <stdbool.h>
#include <stdlib.h>
#include <sys/select.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include "../Array.h"
#include "../Buffer.h"
#include "../io.h"
#include "../popen2.h"
#include "Pager.h"

// Don't use `pager` as it's not available in all systems.
#define EXTERNAL_BINARY "less"

#define PAGING_THRESHOLD 0.6

struct Pager {
    bool has_timer;
    struct Error timer_error;
    pthread_t timer_thread;
    pthread_mutex_t timer_mutex;
    struct Array buffers;
    struct Array* options;
    size_t nr_lines;
    size_t nr_line_chars;
    // Set to `IO_NULL_FD` until the pager starts (if at all).
    int fd;
    pid_t child_pid;
};

static struct winsize terminal;

// FIXME: check `errno`
static void get_terminal_size(int signal_nr) {
    signal(SIGWINCH, get_terminal_size);
    ioctl(STDOUT_FILENO, TIOCGWINSZ, &terminal);
}

static void init_argv(
        struct Array* argv, struct Array* options, struct Error* error) {

    Array_init(argv, error, EXTERNAL_BINARY, NULL);

    if (Error_has(error)) {
        return;
    }

    if (!ARRAY_IS_NULL_INITIALIZED(options)) {
        Array_extend(argv, options, error);

        if (Error_has(error)) {
            Array_deinit(argv);
            return;
        }
    }

    Array_add(argv, argv->length, (intptr_t) NULL, error);

    if (Error_has(error)) {
        Array_deinit(argv);
    }
}

// FIXME
static bool is_available(struct Plugin* plugin, struct Error* error) {
    char* argv[] = {
        EXTERNAL_BINARY,
        "--version",
        NULL,
    };

    return popen2_check(argv[0], argv, error);
}

static void protect_buffer(
        struct Pager* pager, bool do_lock, struct Error* error) {

    if (pager->has_timer) {
        int error_nr = (do_lock ? pthread_mutex_lock : pthread_mutex_unlock)
            (&pager->timer_mutex);

        if (error_nr) {
            Error_add_errno(error, error_nr);
        }
    }
}

static void flush_buffer(
        struct Pager* pager, int default_fd, struct Error* error) {

    protect_buffer(pager, true, error);

    if (Error_has(error)) {
        return;
    }

    if (pager->fd == IO_NULL_FD) {
        pager->fd = default_fd;
    }

    for (size_t i = 0; i < pager->buffers.length; ++i) {
        struct Buffer* buffer = (struct Buffer*) pager->buffers.data[i];

        io_write(
            pager->fd,
            (uint8_t*) buffer->data,
            buffer->length * sizeof(buffer->data[0]),
            error);

        Buffer_delete(buffer);

        if (Error_has(error)) {
            pager->buffers.data[i] = (intptr_t) NULL;
            return;
        }
    }

    pager->buffers.length = 0;
    protect_buffer(pager, false, error);
}

void* flush_buffer_timer(void* arg) {
    struct Pager* pager = (struct Pager*) arg;
    struct timeval timeout;

    timeout.tv_sec = 0;
    timeout.tv_usec = 500 * 1000;

    if (select(0, NULL, NULL, NULL, &timeout) == -1) {
        Error_add_errno(&pager->timer_error, errno);
    }
    else {
        flush_buffer(pager, STDOUT_FILENO, &pager->timer_error);
    }

    return NULL;
}

static bool buffer_input(
        struct Pager* pager, struct Buffer** buffer, struct Error* error) {

    bool should_buffer = true;

    for (size_t i = 0; i < (*buffer)->length; ++i) {
        if ((*buffer)->data[i] == '\n') {
            ++pager->nr_lines;
            pager->nr_line_chars = 0;

            if (pager->nr_lines > (terminal.ws_row * PAGING_THRESHOLD)) {
                should_buffer = false;
                break;
            }
        }
        else {
            ++pager->nr_line_chars;

            if (pager->nr_line_chars > terminal.ws_col) {
                ++pager->nr_lines;
                pager->nr_line_chars = 0;

                if (pager->nr_lines > (terminal.ws_row * PAGING_THRESHOLD)) {
                    should_buffer = false;
                    break;
                }
            }
        }
    }

    if (!should_buffer) {
        return false;
    }

    protect_buffer(pager, true, error);

    if (Error_has(error)) {
        return false;
    }

    Array_add(
        &pager->buffers, pager->buffers.length, (intptr_t) *buffer, error);

    if (Error_has(error)) {
        return false;
    }

    protect_buffer(pager, false, error);

    if (Error_has(error)) {
        return false;
    }

    if (!pager->has_timer) {
        int error_nr = pthread_create(
            &pager->timer_thread, NULL, flush_buffer_timer, pager);

        if (error_nr) {
            Error_add_errno(error, error_nr);
            return false;
        }

        error_nr = pthread_mutex_init(&pager->timer_mutex, NULL);

        // FIXME: stop thread?
        if (error_nr) {
            Error_add_errno(error, error_nr);
            return false;
        }

        pager->has_timer = true;
    }

    *buffer = NULL;
    return true;
}

static void Pager_delete(struct Pager* pager, struct Error* error) {
    if (pager->has_timer) {
        if (Error_has(&pager->timer_error)) {
            // FIXME: don't discard errors
            Error_copy(error, &pager->timer_error);
            return;
        }

        int error_nr = pthread_cancel(pager->timer_thread);

        if (error_nr && (error_nr != ESRCH)) {
            Error_add_errno(error, error_nr);
            return;
        }

        error_nr = pthread_join(pager->timer_thread, NULL);

        if (error_nr) {
            Error_add_errno(error, error_nr);
            return;
        }

        error_nr = pthread_mutex_destroy(&pager->timer_mutex);

        if (error_nr) {
            Error_add_errno(error, error_nr);
            return;
        }
    }

    for (size_t i = 0; i < pager->buffers.length; ++i) {
        Buffer_delete((struct Buffer*) pager->buffers.data[i]);
    }

    Array_deinit(&pager->buffers);

    if ((pager->fd != IO_NULL_FD) && (close(pager->fd) == -1)) {
        Error_add_errno(error, errno);
        return;
    }

    if (pager->child_pid != -1) {
        int status = popen2_wait(pager->child_pid, error);

        if (Error_has(error) || (status != 0)) {
            Error_add_string(error, "`" EXTERNAL_BINARY "`");
            return;
        }
    }

    free(pager);
}

static struct Pager* Pager_new(struct Array* options, struct Error* error) {
    struct Pager* pager = (struct Pager*) malloc(sizeof(*pager));

    if (pager == NULL) {
        Error_add_errno(error, errno);
        return NULL;
    }

    Array_init(&pager->buffers, error, NULL);

    if (Error_has(error)) {
        free(pager);
        return NULL;
    }

    pager->has_timer = false;
    pager->options = options;
    pager->nr_lines = 0;
    pager->nr_line_chars = 0;
    pager->fd = IO_NULL_FD;
    pager->child_pid = -1;

    Error_clear(&pager->timer_error);
    return pager;
}

static void Output_close(struct Output* output, struct Error* error) {
    struct Pager* pager = (struct Pager*) output->arg;
    flush_buffer(pager, STDOUT_FILENO, error);
    Pager_delete(pager, error);
}

static void Output_write(
        struct Output* output, struct Buffer** buffer, struct Error* error) {

    struct Pager* pager = (struct Pager*) output->arg;

    if (pager->fd == IO_NULL_FD) {
        if (buffer_input(pager, buffer, error)) {
            return;
        }

        struct Array argv;
        init_argv(&argv, pager->options, error);

        if (Error_has(error)) {
            return;
        }

        int fd = popen2(
            (char*) argv.data[0],
            (char**) argv.data,
            false,
            IO_NULL_FD,
            IO_NULL_FD,
            &pager->child_pid,
            error);

        if (Error_has(error)) {
            Error_add_errno(error, errno);
            Error_add_string(error, "`" EXTERNAL_BINARY "`");
            Array_deinit(&argv);
            return;
        }

        Array_deinit(&argv);
        flush_buffer(pager, fd, error);

        if (Error_has(error)) {
            return;
        }
    }

    io_write(
        pager->fd,
        (uint8_t*) (*buffer)->data,
        (*buffer)->length * sizeof((*buffer)->data[0]),
        error);

    (*buffer)->length = 0;
}

static void open_named_input(
        struct Plugin* plugin,
        struct Input* input,
        size_t argc,
        char* argv[],
        struct Error* error) {

    /*bool is_tty = io_is_tty(STDOUT_FILENO, error);

    if (Error_has(error) || !is_tty) {
        return;
    }

    // FIXME: may mess up argument order processing if called always
    if (!is_available()) {
        return;
    }

    // FIXME: convert fatal error to warning
    if (signal(SIGWINCH, get_terminal_size) == SIG_ERR) {
        Error_add(error, strerror(errno));
        return;
    }

    // FIXME: cleanup signal handler
    // FIXME: convert fatal error to warning
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &terminal) == -1) {
        Error_add(error, strerror(errno));
        return;
    }

    Output* output = Output_new(plugin, error);

    // FIXME: cleanup signal handler
    if (Error_has(error)) {
        return;
    }

    output->close = Output_close;
    output->write = Output_write;
    output->arg = (intptr_t) Pager_new(&plugin->options, error);

    // FIXME: cleanup signal handler
    if (Error_has(error)) {
        Output_delete(output);
        return;
    }

    Array_add(outputs, outputs->length, (intptr_t) output, error);

    // FIXME: cleanup signal handler
    if (Error_has(error)) {
        Pager_delete((struct Pager*) output->arg, error);
        Output_delete(output);
    }*/
}

struct Plugin Pager_Plugin = {
    "pager",
    "page output via `" EXTERNAL_BINARY "`, when needed",
    (intptr_t) NULL,
    is_available,
    NULL,
    open_named_input,
};
