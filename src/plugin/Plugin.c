#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include "Plugin.h"

void Input_delete(Input* input) {
    free(input);
}

Input* Input_new(char* name, int fd, Error* error) {
    Input* input = (Input*) malloc(sizeof(*input));

    if (input == NULL) {
        ERROR_ERRNO(error, errno);
        return NULL;
    }

    input->arg = (intptr_t) NULL;
    input->name = name;
    input->fd = fd;
    input->close = NULL;

    ERROR_CLEAR(error);
    return input;
}

void Output_delete(Output* output) {
    free(output);
}

Output* Output_new(Error* error) {
    Output* output = (Output*) malloc(sizeof(*output));

    if (output == NULL) {
        ERROR_ERRNO(error, errno);
        return NULL;
    }

    ERROR_CLEAR(error);
    return output;
}
