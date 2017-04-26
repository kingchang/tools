#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "Array.h"
#include "io.h"
#include "options.h"
#include "plugin/Dir.h"
#include "plugin/File.h"
#include "plugin/Pager.h"
#include "plugin/Stdin.h"
#include "plugin/Vcs.h"

static struct Plugin_Setup plugins_setup[] = {
    {&Stdin_Plugin, true, 0, NULL},
    {&File_Plugin, true, 0, NULL},
    {&Dir_Plugin, true, 0, NULL},
    {&Vcs_Plugin, true, 0, NULL},
    {&Pager_Plugin, true, 0, NULL},
};

// Plus one for `stdout` as default.
static struct Output outputs[C_ARRAY_LENGTH(plugins_setup) + 1];

static size_t outputs_length = 0;

static void Stdout_close(struct Output* output, struct Error* error) {
}

static void Stdout_write(
        struct Output* output,
        char* buffer,
        size_t length,
        struct Error* error) {

    io_write_all(output->fd, buffer, length * sizeof(buffer[0]), error);
}

static void close_outputs(struct Error* error) {
    for (size_t i = 0; i < outputs_length; ++i) {
        outputs[i].close(&outputs[i], error);

        if (Error_has(error)) {
            return;
        }
    }
}

static void open_outputs(struct Error* error) {
    for (size_t i = 0; i < C_ARRAY_LENGTH(plugins_setup); ++i) {
        struct Plugin_Setup* plugin_setup = &plugins_setup[i];
        struct Output* output = &outputs[outputs_length];

        output->fd = IO_NULL_FD;

        plugin_setup->plugin->open_output(
            plugin_setup->plugin,
            output,
            plugin_setup->argc,
            plugin_setup->argv,
            error);

        if (Error_has(error)) {
            Error_add_string(error, plugin_setup->plugin->name);
            return;
        }

        if (output->fd != IO_NULL_FD) {
            ++outputs_length;
        }
    }

    struct Output* Stdout = &outputs[outputs_length];
    Stdout->fd = STDOUT_FILENO;
    Stdout->close = Stdout_close;
    Stdout->write = Stdout_write;
    ++outputs_length;
}

static void write_to_outputs(char* buffer, size_t length, struct Error* error) {
    for (size_t i = 0; i < outputs_length; ++i) {
        outputs[i].write(&outputs[i], buffer, length, error);

        if (Error_has(error)) {
            break;
        }
    }
}

/** @return `true` if the input was successfully flushed, `false` otherwise */
static bool flush_input(
        struct Input* input,
        struct Plugin_Setup* plugin_setup,
        struct Error* error) {

    plugin_setup->plugin->open_input(
        plugin_setup->plugin,
        input,
        plugin_setup->argc,
        plugin_setup->argv,
        error);

    if (Error_has(error) || (input->fd == IO_NULL_FD)) {
        return false;
    }

    while (true) {
        char buffer[BUFSIZ];
        size_t nr_read = input->read(input, buffer, BUFSIZ, error);

        if (Error_has(error)) {
            return false;
        }
        if (nr_read == 0) {
            break;
        }

        write_to_outputs(buffer, nr_read, error);

        if (Error_has(error)) {
            return false;
        }
    }

    input->close(input, error);

    if (Error_has_errno(error, ENOENT)) {
        Error_clear(error);
        return false;
    }

    return !Error_has(error);
}

static void flush_inputs(
        size_t inputs_length, char* input_names[], struct Error* error) {

    for (size_t i = 0; i < inputs_length; ++i) {
        bool was_input_flushed = false;
        char* input_name = input_names[i];

        for (size_t j = 0; j < C_ARRAY_LENGTH(plugins_setup); ++j) {
            struct Plugin_Setup* plugin_setup = &plugins_setup[j];

            if (!plugin_setup->is_enabled) {
                continue;
            }

            struct Input input = {
                input_name,
                IO_NULL_FD,
                (intptr_t) NULL,
                NULL,
                NULL,
            };

            was_input_flushed = flush_input(&input, plugin_setup, error);

            if (Error_has(error)) {
                if (input_name != NULL) {
                    Error_add_string(error, input_name);
                }
                Error_add_string(error, plugin_setup->plugin->name);
                return;
            }
            if (was_input_flushed) {
                break;
            }
        }

        if (!was_input_flushed) {
            if (input_name != NULL) {
                Error_add_string(error, "unsupported input");
                Error_add_string(error, input_name);
            }
            return;
        }
    }
}

int main(int argc, char* argv[]) {
    struct Error error = ERROR_INITIALIZER;
    char* plugin_argv_storage[C_ARRAY_LENGTH(plugins_setup) * (argc - 1)];

    for (size_t i = 0; i < C_ARRAY_LENGTH(plugins_setup); ++i) {
        plugins_setup[i].argv = plugin_argv_storage + i * (argc - 1);
    }

    int args_pos = parse_options(
        argc, argv, C_ARRAY_LENGTH(plugins_setup), plugins_setup, &error);

    if ((args_pos < 0) || (Error_has(&error))) {
        return Error_print(&error, stderr) ? EXIT_FAILURE : EXIT_SUCCESS;
    }

    open_outputs(&error);

    if (Error_has(&error)) {
        Error_print(&error, stderr);
        return EXIT_FAILURE;
    }

    if (args_pos == argc) {
        char* input_name = NULL;
        flush_inputs(1, &input_name, &error);
    }
    else {
        flush_inputs((size_t) (argc - args_pos), argv + args_pos, &error);
    }

    if (!Error_has(&error)) {
        close_outputs(&error);
    }

    if (Error_has(&error)) {
        Error_print(&error, stderr);
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
