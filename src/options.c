#include <getopt.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include "Array.h"
#include "io.h"
#include "options.h"

#define HELP_OPT "h"
#define DISABLE_PLUGIN_OPT "d:"
#define PLUGIN_OPTION_OPT "p:"

#define ALL_OPTS ( \
    HELP_OPT \
    DISABLE_PLUGIN_OPT \
    PLUGIN_OPTION_OPT \
)

#define ERROR_UNKNOWN_PLUGIN "No such plugin or disabled."

static void display_help(Plugin* plugins[], size_t nr_plugins) {
    fprintf(stderr,
        "Usage: show [OPTION]... [INPUT]...\n"
        "Version: 0.7.0\n"
        "\n"
        "Options:\n"
        "  -%c            display this help and exit\n"
        "  -%c NAME       disable a plugin\n"
        "  -%c NAME:OPT   pass an option to a plugin\n",
        *HELP_OPT,
        *DISABLE_PLUGIN_OPT,
        *PLUGIN_OPTION_OPT);

    if (nr_plugins > 0) {
        bool needs_header = true;

        for (size_t i = 0; i < nr_plugins; ++i) {
            if (plugins[i] != NULL) {
                if (needs_header) {
                    needs_header = false;

                    fputs(
                        "\n"
                        "Plugins:\n",
                        stderr);
                }

                fprintf(stderr, "  %-14s%s\n",
                    plugins[i]->get_name(),
                    plugins[i]->get_description());
            }
        }
    }
}

static ssize_t find_plugin(
        char* name,
        size_t name_length,
        Plugin* plugins[],
        size_t nr_plugins) {

    for (size_t i = 0; i < nr_plugins; ++i) {
        if (plugins[i] != NULL) {
            const char* other = plugins[i]->get_name();

            if (name_length == 0) {
                if (strcmp(other, name) == 0) {
                    return i;
                }
            }
            else {
                size_t j = 0;

                for (j = 0; (j < name_length) && (other[j] != '\0'); ++j) {
                    if (other[j] != name[j]) {
                        break;
                    }
                }
                if (other[j] == '\0') {
                    return i;
                }
            }
        }
    }

    return -1;
}

static void parse_plugin_option(
        char* option,
        Plugin* plugins[],
        size_t nr_plugins,
        Error* error) {

    const char PLUGIN_OPTION_SEP[] = ":";
    char* separator = strstr(option, PLUGIN_OPTION_SEP);

    bool is_option_missing = (separator == NULL)
        || (separator[STATIC_ARRAY_LENGTH(PLUGIN_OPTION_SEP) - 1] == '\0');

    if (is_option_missing) {
        ERROR_SET(error, "No plugin option specified.");
        return;
    }

    size_t name_length = (separator - option);

    if (name_length == 0) {
        ERROR_SET(error, "No plugin name specified.");
        return;
    }

    ssize_t plugin_pos = find_plugin(option, name_length, plugins, nr_plugins);

    if (plugin_pos < 0) {
        ERROR_SET(error, ERROR_UNKNOWN_PLUGIN);
        return;
    }

    Plugin* plugin = plugins[plugin_pos];
    char* value = separator + STATIC_ARRAY_LENGTH(PLUGIN_OPTION_SEP) - 1;

    if (plugin->options.data == NULL) {
        Array_init(&plugin->options, error, value, NULL);

        if (ERROR_HAS(error)) {
            return;
        }
    }
    else {
        Array_add(
            &plugin->options, plugin->options.length, (intptr_t) value, error);

        if (ERROR_HAS(error)) {
            return;
        }
    }

    ERROR_CLEAR(error);
}

bool parse_options(
        int argc,
        char **argv,
        Plugin **plugins,
        size_t nr_plugins,
        Array* inputs,
        Error *error) {

    int option;

    while ((option = getopt(argc, argv, ALL_OPTS)) != -1) {
        if (option == *DISABLE_PLUGIN_OPT) {
            ssize_t pos = find_plugin(optarg, 0, plugins, nr_plugins);

            if (pos >= 0) {
                Array_deinit(&plugins[pos]->options);
                plugins[pos] = NULL;
            }
            else {
                ERROR_SET(error, ERROR_UNKNOWN_PLUGIN);
                return false;
            }
        }
        else if (option == *HELP_OPT) {
            display_help(plugins, nr_plugins);
            ERROR_CLEAR(error);
            return true;
        }
        else if (option == *PLUGIN_OPTION_OPT) {
            parse_plugin_option(optarg, plugins, nr_plugins, error);

            if (ERROR_HAS(error)) {
                return false;
            }
        }
        else {
            ERROR_SET(error, "Try '-" HELP_OPT "' for more information.");
            return false;
        }
    }

    for (int i = optind; i < argc; ++i) {
        Input* input = Input_new(argv[i], IO_INVALID_FD, error);

        if (ERROR_HAS(error)) {
            return false;
        }

        Array_add(inputs, inputs->length, (intptr_t) input, error);

        if (ERROR_HAS(error)) {
            Input_delete(input);
            return false;
        }
    }

    ERROR_CLEAR(error);
    return false;
}
