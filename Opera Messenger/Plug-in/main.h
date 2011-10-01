#ifndef __MAIN__
#define __MAIN__


#define PLUGIN_NAME "Example"

#define PLUGIN_DESCRIPTION "Sample NP API plug-in."

#define PLUGIN_MIME_TYPE "application/x-example"

#define PLUGIN_MAJOR_VERSION 2009

#define PLUGIN_MINOR_VERSION 03

#define PLUGIN_MICRO_VERSION 01

#define PLUGIN_VERSION \
    PLUGIN_VERSION_IMPLEMENTATION( \
        PLUGIN_MAJOR_VERSION, PLUGIN_MINOR_VERSION, PLUGIN_MICRO_VERSION)

#define PLUGIN_VERSION_IMPLEMENTATION(major, minor, micro) \
    PLUGIN_VERSION_TO_STRING(major) "-" \
    PLUGIN_VERSION_TO_STRING(minor) "-" \
    PLUGIN_VERSION_TO_STRING(micro)

#define PLUGIN_VERSION_TO_STRING(version) #version


#endif
