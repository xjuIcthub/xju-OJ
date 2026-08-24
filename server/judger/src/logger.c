#define _GNU_SOURCE
#define _POSIX_SOURCE
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <sys/file.h>

#include "logger.h"

#define LOG_BUFFER_SIZE 8192


FILE *log_open(const char *filename) {
    FILE *log_fp = fopen(filename, "ae");
    if (log_fp == NULL) {
        fprintf(stderr, "can not open log file %s", filename);
    }
    return log_fp;
}


void log_close(FILE *log_fp) {
    if (log_fp != NULL) {
        fclose(log_fp);
    }
}


void log_write(int level, const char *source_filename, const int line,
               const FILE *log_fp, const char *fmt, ...) {
    static const char LOG_LEVEL_NOTE[][10] = {"FATAL", "WARNING", "INFO", "DEBUG"};
    if (log_fp == NULL) {
        fprintf(stderr, "can not open log file");
        return;
    }

    char buffer[LOG_BUFFER_SIZE];
    char message[LOG_BUFFER_SIZE];
    char datetime[100];
    struct tm local_time;
    time_t now = time(NULL);
    if (localtime_r(&now, &local_time) == NULL) {
        snprintf(datetime, sizeof(datetime), "unknown-time");
    }
    else {
        strftime(datetime, sizeof(datetime), "%Y-%m-%d %H:%M:%S", &local_time);
    }

    va_list ap;
    va_start(ap, fmt);
    vsnprintf(message, sizeof(message), fmt, ap);
    va_end(ap);

    int count = snprintf(buffer, sizeof(buffer), "%s [%s] [%s:%d]%s\n",
                         LOG_LEVEL_NOTE[level], datetime, source_filename, line, message);
    if (count < 0) {
        return;
    }
    size_t length = (size_t) count;
    if (length >= sizeof(buffer)) {
        length = sizeof(buffer) - 1;
    }

    int log_fd = fileno((FILE *) log_fp);
    if (flock(log_fd, LOCK_EX) != 0) {
        fprintf(stderr, "flock error");
        return;
    }

    size_t offset = 0;
    while (offset < length) {
        ssize_t written = write(log_fd, buffer + offset, length - offset);
        if (written > 0) {
            offset += (size_t) written;
        }
        else if (written < 0 && errno == EINTR) {
            continue;
        }
        else {
            fprintf(stderr, "write error");
            break;
        }
    }
    (void) flock(log_fd, LOCK_UN);
}
