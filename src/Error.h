#pragma once
#include <stdio.h>

#define ERROR_MESSAGE_STACK_SIZE 8
#define ERROR_INITIALIZER {NULL}

// Successful calls must not clear errors.
// Ordered by most to least recent error message.
typedef const char* Error[ERROR_MESSAGE_STACK_SIZE];

#define ERROR_CLEAR(error) ((void) ((*(error))[0] = NULL))
#define ERROR_GET_LAST(error) ((*(error))[0])
#define ERROR_HAS(error) ((*(error))[0] != NULL)

void Error_add(Error* error, const char* message);
void Error_copy(Error* error, Error* source);

// Errors while printing are silently discarded.
void Error_print(Error* error, FILE* stream);
