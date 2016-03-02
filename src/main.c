#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "Array.h"
#include "Options.h"
#include "plugin/File_Plugin.h"
#include "plugin/Ls_Plugin.h"
#include "plugin/Pipe_Plugin.h"


Plugin* plugins[] = {
    &Pipe_Plugin,
    &File_Plugin,
    &Ls_Plugin,
};


static void cleanup(Array args, Array fds_in, Error error) {
    if (error) {
        fprintf(stderr, "%s\n", error);
    }

    Array_delete(args);
    Array_delete(fds_in);

    for (size_t i = 0; i < STATIC_ARRAY_LENGTH(plugins); ++i) {
        if (plugins[i]) {
            Array_delete(plugins[i]->options);
            plugins[i] = NULL;
        }
    }
}


static Array list_input_fds(Error* error) {
    Array fds_in = Array_new(error, NULL);

    if (Error_has(error)) {
        return NULL;
    }

    Array_add(fds_in, STDIN_FILENO, error);

    if (Error_has(error)) {
        Array_delete(fds_in);
        return NULL;
    }

    Error_clear(error);
    return fds_in;
}


int main(int argc, char* argv[]) {
    Error error;
    Array args = Options_parse(
        argc, argv, plugins, STATIC_ARRAY_LENGTH(plugins), &error);

    if (args == NULL) {
        cleanup(NULL, NULL, error ? error : NULL);
        return EXIT_SUCCESS;
    }

    Array fds_in = list_input_fds(&error);

    if (error) {
        cleanup(args, NULL, error);
        return EXIT_FAILURE;
    }

    for (size_t i = 0; i < STATIC_ARRAY_LENGTH(plugins); ++i) {
        if (!plugins[i]) {
            continue;
        }

        Plugin_Result result = plugins[i]->run(
            args,
            plugins[i]->options,
            fds_in,
            &error);

        if (error) {
            fprintf(stderr, "%s: %s\n", plugins[i]->get_name(), error);
            cleanup(args, fds_in, NULL);
            return EXIT_FAILURE;
        }

        if ((result.args != NULL) && (result.args != args)) {
            Array_delete(args);
            args = result.args;
        }

        if ((result.fds_in != NULL) && (result.fds_in != fds_in)) {
            Array_delete(fds_in);
            fds_in = result.fds_in;
        }
    }

    for (size_t i = 0; i < fds_in->length; ++i) {
        int fd_in = (int) fds_in->data[i];
        ssize_t nr_bytes_read;
        const int BUFFER_SIZE = 256;
        char buffer[BUFFER_SIZE + 1];

        while ((nr_bytes_read = read(fd_in, buffer, BUFFER_SIZE)) > 0) {
            buffer[nr_bytes_read] = '\0';
            fputs(buffer, stdout);
        }
    }

    cleanup(args, fds_in, NULL);
    return EXIT_SUCCESS;
}
