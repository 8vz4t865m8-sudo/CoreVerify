#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成极简的 Apple 风格 libc 头，供 Linux 上的 clang 做 Objective-C 语法检查。

★ 为什么不直接用宿主 /usr/include？
  因为宿主是 glibc，而 glibc 的头里用了大量 Apple clang 不认识的写法
  （__nonnull / __wur / __THROW / gnu/stubs-32.h …），
  一旦 -target 切到 arm64-apple-ios，这些头就会集体报错。

★ 所以这里只声明本工程真正用到的那部分 libc 符号。
  目的不是运行，而是让 clang 能过语法分析。
"""

import os

ROOT = os.environ.get("CV_LIBC_DIR", "/tmp/cvlibc")

FILES = {}

FILES["stdio.h"] = r'''
/* 极简 stdio.h —— 只保留 CoreVerify 工程真正用到的声明 */
#ifndef _CV_STDIO_H
#define _CV_STDIO_H
#include <stddef.h>
#include <stdarg.h>
typedef struct _CV_FILE FILE;
#define stderr ((FILE *)0)
#define stdout ((FILE *)0)
#define EOF (-1)
#define SEEK_SET 0
#define SEEK_CUR 1
#define SEEK_END 2
#define BUFSIZ 8192
extern FILE *fopen(const char *, const char *);
extern int   fclose(FILE *);
extern size_t fread(void *, size_t, size_t, FILE *);
extern size_t fwrite(const void *, size_t, size_t, FILE *);
extern int   fputs(const char *, FILE *);
extern int   fputc(int, FILE *);
extern int   fprintf(FILE *, const char *, ...);
extern int   printf(const char *, ...);
extern int   snprintf(char *, size_t, const char *, ...);
extern int   vsnprintf(char *, size_t, const char *, va_list);
extern int   sprintf(char *, const char *, ...);
extern int   sscanf(const char *, const char *, ...);
extern int   fflush(FILE *);
extern int   fseek(FILE *, long, int);
extern long  ftell(FILE *);
extern int   remove(const char *);
extern int   rename(const char *, const char *);
extern FILE *tmpfile(void);
#endif
'''

FILES["string.h"] = r'''
#ifndef _CV_STRING_H
#define _CV_STRING_H
#include <stddef.h>
extern size_t strlen(const char *);
extern int    strcmp(const char *, const char *);
extern int    strncmp(const char *, const char *, size_t);
extern char  *strcpy(char *, const char *);
extern char  *strncpy(char *, const char *, size_t);
extern char  *strcat(char *, const char *);
extern char  *strncat(char *, const char *, size_t);
extern char  *strchr(const char *, int);
extern char  *strrchr(const char *, int);
extern char  *strstr(const char *, const char *);
extern void  *memcpy(void *, const void *, size_t);
extern void  *memmove(void *, const void *, size_t);
extern void  *memset(void *, int, size_t);
extern int    memcmp(const void *, const void *, size_t);
extern char  *strerror(int);
extern int    strcasecmp(const char *, const char *);
#endif
'''

FILES["stdlib.h"] = r'''
#ifndef _CV_STDLIB_H
#define _CV_STDLIB_H
#include <stddef.h>
extern void  *malloc(size_t);
extern void  *calloc(size_t, size_t);
extern void  *realloc(void *, size_t);
extern void   free(void *);
extern void   exit(int);
extern void   abort(void);
extern int    atoi(const char *);
extern long   atol(const char *);
extern double atof(const char *);
extern char  *getenv(const char *);
extern int    abs(int);
extern long   labs(long);
#endif
'''

FILES["limits.h"] = r'''
#ifndef _CV_LIMITS_H
#define _CV_LIMITS_H
#define CHAR_BIT   8
#define SCHAR_MAX  127
#define UCHAR_MAX  255
#define SHRT_MAX   32767
#define INT_MAX    2147483647
#define INT_MIN    (-2147483647-1)
#define UINT_MAX   4294967295U
#define LONG_MAX   9223372036854775807L
#define LONG_MIN   (-9223372036854775807L-1)
#define ULONG_MAX  18446744073709551615UL
#define LLONG_MAX  9223372036854775807LL
#define PATH_MAX   1024
#endif
'''

FILES["time.h"] = r'''
#ifndef _CV_TIME_H
#define _CV_TIME_H
#include <stddef.h>
typedef long time_t;
typedef long clock_t;
struct tm {
    int tm_sec, tm_min, tm_hour, tm_mday, tm_mon, tm_year;
    int tm_wday, tm_yday, tm_isdst;
};
extern time_t time(time_t *);
extern struct tm *localtime(const time_t *);
extern struct tm *gmtime(const time_t *);
extern size_t strftime(char *, size_t, const char *, const struct tm *);
#endif
'''

FILES["math.h"] = r'''
#ifndef _CV_MATH_H
#define _CV_MATH_H
extern double fabs(double);
extern double floor(double);
extern double ceil(double);
extern double round(double);
extern double pow(double, double);
extern double sqrt(double);
extern double fmod(double, double);
extern double sin(double);
extern double cos(double);
#endif
'''

FILES["assert.h"] = r'''
#ifndef _CV_ASSERT_H
#define _CV_ASSERT_H
extern void __cv_assert_fail(const char *, const char *, int);
#define assert(e) ((void)0)
#endif
'''

FILES["ctype.h"] = r'''
#ifndef _CV_CTYPE_H
#define _CV_CTYPE_H
extern int isdigit(int);
extern int isalpha(int);
extern int isalnum(int);
extern int isspace(int);
extern int isupper(int);
extern int islower(int);
extern int toupper(int);
extern int tolower(int);
#endif
'''

FILES["errno.h"] = r'''
#ifndef _CV_ERRNO_H
#define _CV_ERRNO_H
extern int *__cv_errno_location(void);
#define errno (*__cv_errno_location())
#define ENOENT 2
#define EIO 5
#define ENOMEM 12
#define EINVAL 22
#endif
'''

FILES["stdbool.h"] = r'''
#ifndef _CV_STDBOOL_H
#define _CV_STDBOOL_H
#define bool _Bool
#define true 1
#define false 0
#define __bool_true_false_are_defined 1
#endif
'''

FILES["inttypes.h"] = '#pragma once\n#include <stdint.h>\n'
FILES["strings.h"] = '#pragma once\n#include <string.h>\n'
FILES["unistd.h"] = r'''
#ifndef _CV_UNISTD_H
#define _CV_UNISTD_H
#include <stddef.h>
typedef long ssize_t;
typedef int pid_t;
extern int   getpid(void);
extern unsigned sleep(unsigned);
extern int   usleep(unsigned);
extern ssize_t write(int, const void *, size_t);
extern ssize_t read(int, void *, size_t);
extern int   close(int);
extern int   unlink(const char *);
#endif
'''
FILES["sys/types.h"] = r'''
#ifndef _CV_SYS_TYPES_H
#define _CV_SYS_TYPES_H
#include <stddef.h>
typedef long ssize_t;
typedef int  pid_t;
typedef unsigned int mode_t;
typedef long off_t;
#endif
'''
FILES["sys/time.h"] = r'''
#ifndef _CV_SYS_TIME_H
#define _CV_SYS_TIME_H
#include <time.h>
struct timeval { long tv_sec; long tv_usec; };
extern int gettimeofday(struct timeval *, void *);
#endif
'''
FILES["pthread.h"] = r'''
#ifndef _CV_PTHREAD_H
#define _CV_PTHREAD_H
typedef unsigned long pthread_t;
typedef struct { long v; } pthread_mutex_t;
typedef struct { long v; } pthread_cond_t;
extern int pthread_mutex_init(pthread_mutex_t *, const void *);
extern int pthread_mutex_lock(pthread_mutex_t *);
extern int pthread_mutex_unlock(pthread_mutex_t *);
extern int pthread_mutex_destroy(pthread_mutex_t *);
#endif
'''


def write_all():
    n = 0
    for rel, content in FILES.items():
        p = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        n += 1
    return n


if __name__ == "__main__":
    cnt = write_all()
    print("已生成 %d 个 libc stub 头到 %s" % (cnt, ROOT))
