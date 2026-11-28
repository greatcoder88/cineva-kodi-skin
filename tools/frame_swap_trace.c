/* Test-only trace of Kodi's Linux presentation calls. No skin changes. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static unsigned long long monotonic_ns(void)
{
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (unsigned long long)now.tv_sec * 1000000000ULL + now.tv_nsec;
}

static void record_swap(unsigned long long start, const char *api)
{
    static FILE *trace;
    static int initialized;
    unsigned long long end = monotonic_ns();

    if (!initialized) {
        const char *data_home = getenv("XDG_DATA_HOME");
        initialized = 1;
        if (data_home) {
            char path[4096];
            int length = snprintf(path, sizeof(path), "%s/frame-swaps.tsv", data_home);
            if (length > 0 && (size_t)length < sizeof(path))
                trace = fopen(path, "a");
        }
    }
    if (trace) {
        fprintf(trace, "%llu\t%llu\t%s\n", start, end, api);
        fflush(trace);
    }
}

void glXSwapBuffers(void *display, unsigned long drawable)
{
    static void (*next)(void *, unsigned long);
    if (!next)
        next = dlsym(RTLD_NEXT, "glXSwapBuffers");
    if (next) {
        unsigned long long start = monotonic_ns();
        next(display, drawable);
        record_swap(start, "GLX");
    }
}

unsigned int eglSwapBuffers(void *display, void *surface)
{
    static unsigned int (*next)(void *, void *);
    if (!next)
        next = dlsym(RTLD_NEXT, "eglSwapBuffers");
    if (!next)
        return 0;
    unsigned long long start = monotonic_ns();
    unsigned int result = next(display, surface);
    if (result)
        record_swap(start, "EGL");
    return result;
}
