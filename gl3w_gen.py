#!/usr/bin/env python

#   gl3w-mx
#   https://github.com/mologie/gl3w-mx
#   Oliver Kuckertz, <oliver.kuckertz@mologie.de>, 2015
#
#   This is a fork of the gl3w tool. The original is available at:
#   https://github.com/skaslev/gl3w
#
#   This fork extends GL3W by a per-context function pointer list, as
#   required by WGL for using multiple drivers in a single application.
#
#   The available API mirrors GLEW's MX mode.
#
#   Usage:
#   1. For each GL context you create, allocate one GL3WContext
#   2. After creating the GL context, call gl3wInit(&yourGl3wContext),
#      and check for a zero return value.
#   3. Create a thread-local variable returning a pointer to a GL3WContext
#      for the current GL context.
#   4. Whenever your thread's GL context changes, update the variable to
#      point to the correct GL3WContext structure.
#   5. Tell GL3W-mx how to retrieve the current context, using for example:
#      #define GL3W_CONTEXT_METHOD myActiveContext()
#      ...where myActiveContext returns the contents of your thread-local
#      variable.

#   This is free and unencumbered software released into the public domain.
#
#   Anyone is free to copy, modify, publish, use, compile, sell, or
#   distribute this software, either in source code form or as a compiled
#   binary, for any purpose, commercial or non-commercial, and by any
#   means.
#
#   In jurisdictions that recognize copyright laws, the author or authors
#   of this software dedicate any and all copyright interest in the
#   software to the public domain. We make this dedication for the benefit
#   of the public at large and to the detriment of our heirs and
#   successors. We intend this dedication to be an overt act of
#   relinquishment in perpetuity of all present and future rights to this
#   software under copyright law.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#   EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#   MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#   IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
#   OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#   ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#   OTHER DEALINGS IN THE SOFTWARE.

# Allow Python 2.6+ to use the print() function
from __future__ import print_function

import re
import os

# Try to import Python 3 library urllib.request
# and if it fails, fall back to Python 2 urllib2
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

# UNLICENSE copyright header
UNLICENSE = br'''/*

    This file was generated with gl3w_gen.py, part of gl3w
    (hosted at https://github.com/skaslev/gl3w)

    This is free and unencumbered software released into the public domain.

    Anyone is free to copy, modify, publish, use, compile, sell, or
    distribute this software, either in source code form or as a compiled
    binary, for any purpose, commercial or non-commercial, and by any
    means.

    In jurisdictions that recognize copyright laws, the author or authors
    of this software dedicate any and all copyright interest in the
    software to the public domain. We make this dedication for the benefit
    of the public at large and to the detriment of our heirs and
    successors. We intend this dedication to be an overt act of
    relinquishment in perpetuity of all present and future rights to this
    software under copyright law.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
    IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
    OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
    OTHER DEALINGS IN THE SOFTWARE.

*/

'''

# Create directories
if not os.path.exists('include/GL'):
    os.makedirs('include/GL')
if not os.path.exists('src'):
    os.makedirs('src')

# Download glcorearb.h
if not os.path.exists('include/GL/glcorearb.h'):
    print('Downloading glcorearb.h to include/GL...')
    web = urllib2.urlopen('https://www.opengl.org/registry/api/GL/glcorearb.h')
    with open('include/GL/glcorearb.h', 'wb') as f:
        f.writelines(web.readlines())
else:
    print('Reusing glcorearb.h from include/GL...')

# Parse function names from glcorearb.h
print('Parsing glcorearb.h header...')
procs = []
p = re.compile(r'GLAPI.*APIENTRY\s+(\w+)')
with open('include/GL/glcorearb.h', 'r') as f:
    for line in f:
        m = p.match(line)
        if m:
            procs.append(m.group(1))
procs.sort()

def proc_t(proc):
    return { 'p': proc,
             'p_s': 'gl3w' + proc[2:],
             'p_t': 'PFN' + proc.upper() + 'PROC' }

# Generate gl3w.h
print('Generating gl3w.h in include/GL...')
with open('include/GL/gl3w.h', 'wb') as f:
    f.write(UNLICENSE)
    f.write(br'''#ifndef __gl3w_h_
#define __gl3w_h_

#include <GL/glcorearb.h>

#ifndef __gl_h_
#define __gl_h_
#endif

#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct _GL3WContext {
    int major;
    int minor;
''')
    for proc in procs:
        f.write('    {0[p_t]: <52} {0[p_s]};\n'.format(proc_t(proc)).encode("utf-8"))
    f.write(br'''
} GL3WContext;

''')

    for proc in procs:
        f.write('#define {0[p]: <45} ((GL3W_CONTEXT_METHOD)->{0[p_s]})\n'.format(proc_t(proc)).encode("utf-8"))
    f.write(br'''

typedef void (*GL3WglProc)(void);

/* gl3w api */
int gl3wInit(GL3WContext *context);
void gl3wShutdown(GL3WContext *context);
int gl3wIsSupported(const GL3WContext *context, int major, int minor);
GL3WglProc gl3wGetProcAddress(const char *proc);

#ifdef __cplusplus
}
#endif

#endif
''')

# Generate gl3w.c
print('Generating gl3w.c in src...')
with open('src/gl3w.c', 'wb') as f:
    f.write(UNLICENSE)
    f.write(br'''#include <GL/gl3w.h>

#ifdef _WIN32

#define WIN32_LEAN_AND_MEAN 1
#include <windows.h>

static HMODULE libgl;

static void libgl_open(void) {
    libgl = LoadLibraryA("opengl32.dll");
}

static void libgl_close(void) {
    FreeLibrary(libgl);
}

static GL3WglProc libgl_sym(const char *proc) {
    GL3WglProc res;

    res = (GL3WglProc)wglGetProcAddress(proc);
    if (!res)
        res = (GL3WglProc)GetProcAddress(libgl, proc);
    return res;
}

#elif defined(__APPLE__) || defined(__APPLE_CC__)

#include <Carbon/Carbon.h>

static CFBundleRef bundle;
static CFURLRef bundleURL;

static void libgl_open(void) {
    bundleURL = CFURLCreateWithFileSystemPath(kCFAllocatorDefault,
        CFSTR("/System/Library/Frameworks/OpenGL.framework"),
        kCFURLPOSIXPathStyle, true);

    bundle = CFBundleCreate(kCFAllocatorDefault, bundleURL);
    assert(bundle != NULL);
}

static void libgl_close(void) {
    CFRelease(bundle);
    CFRelease(bundleURL);
}

static GL3WglProc libgl_sym(const char *proc) {
    GL3WglProc res;

    CFStringRef procName = CFStringCreateWithCString(kCFAllocatorDefault, proc,
        kCFStringEncodingASCII);
    res = (GL3WglProc)CFBundleGetFunctionPointerForName(bundle, procName);
    CFRelease(procName);
    return res;
}

#else

#include <dlfcn.h>
#include <GL/glx.h>

static void *libgl;

static void libgl_open(void) {
    libgl = dlopen("libGL.so.1", RTLD_LAZY | RTLD_GLOBAL);
}

static void libgl_close(void) {
    dlclose(libgl);
}

static GL3WglProc libgl_sym(const char *proc) {
    GL3WglProc res;

    res = (GL3WglProc)glXGetProcAddress((const GLubyte *)proc);
    if (!res)
        res = (GL3WglProc)dlsym(libgl, proc);
    return res;
}

#endif

''')

    f.write(br'''
static int setup_context(GL3WContext *p) {
''')

    for proc in procs:
        f.write('    p->{0[p_s]} = ({0[p_t]})libgl_sym("{0[p]}");\n'.format(proc_t(proc)).encode("utf-8"))

    f.write(br'''

    if (!p->gl3wGetIntegerv)
        return 0;

    p->gl3wGetIntegerv(GL_MAJOR_VERSION, &p->major);
    p->gl3wGetIntegerv(GL_MINOR_VERSION, &p->minor);

    if (p->major < 3)
        return 0;

    return 1;
}

int gl3wInit(GL3WContext *context) {
    int res;
    libgl_open();
    memset(context, 0, sizeof(*context));
    res = setup_context(context);
    return res;
}

void gl3wShutdown(GL3WContext *context) {
    libgl_close();
    memset(context, 0, sizeof(*context));
}

int gl3wIsSupported(const GL3WContext *context, int major, int minor) {
    if (context->major < 3)
        return 0;

    if (context->major == major)
        return context->minor >= minor;
    else
        return context->major >= major;
}

GL3WglProc gl3wGetProcAddress(const char *proc) {
    return libgl_sym(proc);
}
''')
