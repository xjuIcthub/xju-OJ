#define _DEFAULT_SOURCE
#define _POSIX_SOURCE
#define _GNU_SOURCE
#include <stdio.h>
#include <stdarg.h>
#include <signal.h>
#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>
#include <string.h>
#include <grp.h>
#include <dlfcn.h>
#include <errno.h>
#include <sched.h>
#include <dirent.h>
#include <limits.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/mount.h>

#include "runner.h"
#include "child.h"
#include "logger.h"
#include "filesystem.h"
#include "rules/seccomp_rules.h"

#include "killer.h"


static int close_inherited_fds(unsigned int first_fd) {
    if (close_range(first_fd, ~0U, 0) == 0) {
        return 0;
    }
    if (errno != ENOSYS && errno != EINVAL) {
        return -1;
    }

    DIR *fd_dir = opendir("/proc/self/fd");
    if (fd_dir == NULL) {
        return -1;
    }
    int directory_fd = dirfd(fd_dir);
    struct dirent *entry;
    while ((entry = readdir(fd_dir)) != NULL) {
        char *end = NULL;
        errno = 0;
        long fd = strtol(entry->d_name, &end, 10);
        if (errno == 0 && end != entry->d_name && *end == '\0' &&
            fd >= (long) first_fd && fd <= INT_MAX && fd != directory_fd) {
            close((int) fd);
        }
    }
    return closedir(fd_dir);
}


static int open_redirect_path(const char *path, int flags, mode_t mode) {
    int fd = open(path, flags | O_CLOEXEC | O_NOFOLLOW, mode);
    if (fd < 0) {
        return -1;
    }

    struct stat file_stat;
    if (fstat(fd, &file_stat) != 0) {
        int saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return -1;
    }
    if (!S_ISREG(file_stat.st_mode) && !S_ISCHR(file_stat.st_mode)) {
        close(fd);
        errno = EINVAL;
        return -1;
    }
    return fd;
}


void child_process(int error_fd, struct config *_config) {
    if (error_fd != STDERR_FILENO + 1) {
        int relocated_error_fd = fcntl(error_fd, F_DUPFD_CLOEXEC, STDERR_FILENO + 1);
        if (relocated_error_fd < 0) {
            CHILD_ERROR_EXIT(PIPE_FAILED);
        }
        close(error_fd);
        error_fd = relocated_error_fd;
    }

    if (setpgid(0, 0) != 0) {
        CHILD_ERROR_EXIT(PROCESS_GROUP_FAILED);
    }

    if (_config->max_stack != UNLIMITED) {
        struct rlimit max_stack;
        max_stack.rlim_cur = max_stack.rlim_max = (rlim_t) (_config->max_stack);
        if (setrlimit(RLIMIT_STACK, &max_stack) != 0) {
            CHILD_ERROR_EXIT(SETRLIMIT_FAILED);
        }
    }

    // set memory limit
    // if memory_limit_check_only == 0, we only check memory usage number, because setrlimit(maxrss) will cause some crash issues
    if (_config->memory_limit_check_only == 0) {
        if (_config->max_memory != UNLIMITED) {
            struct rlimit max_memory;
            max_memory.rlim_cur = max_memory.rlim_max = (rlim_t) (_config->max_memory) * 2;
            if (setrlimit(RLIMIT_AS, &max_memory) != 0) {
                CHILD_ERROR_EXIT(SETRLIMIT_FAILED);
            }
        }
    }

    // set cpu time limit (in seconds)
    if (_config->max_cpu_time != UNLIMITED) {
        struct rlimit max_cpu_time;
        // The parent enforces the millisecond process-group CPU budget using
        // /proc accounting. RLIMIT_CPU is a one-second-later fail-safe.
        max_cpu_time.rlim_cur = max_cpu_time.rlim_max =
            (rlim_t) ((_config->max_cpu_time + 999) / 1000 + 1);
        if (setrlimit(RLIMIT_CPU, &max_cpu_time) != 0) {
            CHILD_ERROR_EXIT(SETRLIMIT_FAILED);
        }
    }

    // set max process number limit
    if (_config->max_process_number != UNLIMITED) {
        struct rlimit max_process_number;
        max_process_number.rlim_cur = max_process_number.rlim_max = (rlim_t) _config->max_process_number;
        if (setrlimit(RLIMIT_NPROC, &max_process_number) != 0) {
            CHILD_ERROR_EXIT(SETRLIMIT_FAILED);
        }
    }

    // set max output size limit
    if (_config->max_output_size != UNLIMITED) {
        struct rlimit max_output_size;
        max_output_size.rlim_cur = max_output_size.rlim_max = (rlim_t ) _config->max_output_size;
        if (setrlimit(RLIMIT_FSIZE, &max_output_size) != 0) {
            CHILD_ERROR_EXIT(SETRLIMIT_FAILED);
        }
    }

    if (_config->cwd != NULL && chdir(_config->cwd) != 0) {
        CHILD_ERROR_EXIT(CHDIR_FAILED);
    }

    if (_config->input_path != NULL) {
        int input_fd = open_redirect_path(_config->input_path, O_RDONLY, 0);
        if (input_fd < 0 || dup2(input_fd, STDIN_FILENO) < 0) {
            if (input_fd >= 0) {
                close(input_fd);
            }
            CHILD_ERROR_EXIT(DUP2_FAILED);
        }
        close(input_fd);
    }

    if (_config->output_path != NULL) {
        int output_fd = open_redirect_path(_config->output_path,
                                           O_WRONLY | O_CREAT | O_TRUNC, 0600);
        if (output_fd < 0 || dup2(output_fd, STDOUT_FILENO) < 0) {
            if (output_fd >= 0) {
                close(output_fd);
            }
            CHILD_ERROR_EXIT(DUP2_FAILED);
        }
        close(output_fd);
    }

    if (_config->error_path != NULL) {
        if (_config->output_path != NULL &&
            strcmp(_config->output_path, _config->error_path) == 0) {
            if (dup2(STDOUT_FILENO, STDERR_FILENO) < 0) {
                CHILD_ERROR_EXIT(DUP2_FAILED);
            }
        }
        else {
            int error_output_fd = open_redirect_path(_config->error_path,
                                                     O_WRONLY | O_CREAT | O_TRUNC, 0600);
            if (error_output_fd < 0 || dup2(error_output_fd, STDERR_FILENO) < 0) {
                if (error_output_fd >= 0) {
                    close(error_output_fd);
                }
                CHILD_ERROR_EXIT(DUP2_FAILED);
            }
            close(error_output_fd);
        }
    }

    // Popen closes inherited service descriptors; the native boundary remains
    // fail-closed on kernels without close_range by enumerating /proc/self/fd.
    if (close_inherited_fds(STDERR_FILENO + 2) != 0) {
        CHILD_ERROR_EXIT(DUP2_FAILED);
    }

    if (_config->seccomp_rule_name != NULL &&
        (strcmp("c_cpp_file_io", _config->seccomp_rule_name) == 0 ||
         strcmp("general_file_io", _config->seccomp_rule_name) == 0 ||
         strcmp("golang_file_io", _config->seccomp_rule_name) == 0 ||
         strcmp("node_file_io", _config->seccomp_rule_name) == 0 ||
         strcmp("java", _config->seccomp_rule_name) == 0 ||
         strcmp("java_file_io", _config->seccomp_rule_name) == 0)) {
        if (restrict_file_writes_to_cwd() != 0) {
            CHILD_ERROR_EXIT(LOAD_SECCOMP_FAILED);
        }
    }

    // Drop supplementary groups before setting all real/effective/saved IDs.
    if (_config->gid != (gid_t) -1) {
        gid_t group_list[] = {_config->gid};
        if (setgroups(sizeof(group_list) / sizeof(gid_t), group_list) == -1 ||
            setresgid(_config->gid, _config->gid, _config->gid) == -1) {
            CHILD_ERROR_EXIT(SETUID_FAILED);
        }
    }
    else if (setgroups(0, NULL) == -1) {
        CHILD_ERROR_EXIT(SETUID_FAILED);
    }

    if (_config->uid != (uid_t) -1 &&
        setresuid(_config->uid, _config->uid, _config->uid) == -1) {
        CHILD_ERROR_EXIT(SETUID_FAILED);
    }

    // Runtime-created scratch files remain private to the dropped UID. Fixed
    // judge-controlled input/output files are pre-created and opened above.
    umask(0077);

    // Fail before loading seccomp when the target user or mount cannot execute
    // the configured binary. This keeps EACCES/noexec failures diagnostic.
    if (access(_config->exe_path, X_OK) != 0) {
        CHILD_ERROR_EXIT(EXECVE_FAILED);
    }

    // load seccomp
    if (_config->seccomp_rule_name != NULL) {
        if (strcmp("c_cpp", _config->seccomp_rule_name) == 0) {
            if (c_cpp_seccomp_rules(_config) != SUCCESS) {
                CHILD_ERROR_EXIT(LOAD_SECCOMP_FAILED);
            }
        }
        else if (strcmp("c_cpp_file_io", _config->seccomp_rule_name) == 0) {
            if (c_cpp_file_io_seccomp_rules(_config) != SUCCESS) {
                CHILD_ERROR_EXIT(LOAD_SECCOMP_FAILED);
            }
        }
        else if (strcmp("general", _config->seccomp_rule_name) == 0 ||
                 strcmp("general_file_io", _config->seccomp_rule_name) == 0) {
            if (general_seccomp_rules(_config) != SUCCESS ) {
                CHILD_ERROR_EXIT(LOAD_SECCOMP_FAILED);
            }
        }
        else if (strcmp("golang", _config->seccomp_rule_name) == 0 ||
                 strcmp("golang_file_io", _config->seccomp_rule_name) == 0) {
            if (golang_seccomp_rules(_config) != SUCCESS ) {
                CHILD_ERROR_EXIT(LOAD_SECCOMP_FAILED);
            }
        }
        else if (strcmp("node", _config->seccomp_rule_name) == 0 ||
                 strcmp("node_file_io", _config->seccomp_rule_name) == 0) {
            if (node_seccomp_rules(_config) != SUCCESS ) {
                CHILD_ERROR_EXIT(LOAD_SECCOMP_FAILED);
            }
        }
        else if (strcmp("java", _config->seccomp_rule_name) == 0 ||
                 strcmp("java_file_io", _config->seccomp_rule_name) == 0) {
            if (java_seccomp_rules(_config) != SUCCESS ) {
                CHILD_ERROR_EXIT(LOAD_SECCOMP_FAILED);
            }
        }
        // other rules
        else {
            // rule does not exist
            CHILD_ERROR_EXIT(LOAD_SECCOMP_FAILED);
        }
    }

    execve(_config->exe_path, _config->args, _config->env);
    CHILD_ERROR_EXIT(EXECVE_FAILED);
}
