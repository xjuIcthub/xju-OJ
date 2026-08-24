#ifndef JUDGER_CHILD_H
#define JUDGER_CHILD_H

#include "runner.h"

#define CHILD_ERROR_EXIT(error_code) \
    do { \
        int saved_errno = errno; \
        struct child_error child_error_info = {(error_code), saved_errno}; \
        const char *error_bytes = (const char *) &child_error_info; \
        size_t error_written = 0; \
        while (error_written < sizeof(child_error_info)) { \
            ssize_t write_size = write(error_fd, error_bytes + error_written, \
                                       sizeof(child_error_info) - error_written); \
            if (write_size > 0) { \
                error_written += (size_t) write_size; \
            } \
            else if (write_size < 0 && errno == EINTR) { \
                continue; \
            } \
            else { \
                break; \
            } \
        } \
        _exit(EXIT_FAILURE); \
    } while (0)


void child_process(int error_fd, struct config *_config);

#endif //JUDGER_CHILD_H
