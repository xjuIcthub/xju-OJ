#define _GNU_SOURCE
#define _POSIX_SOURCE

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/wait.h>

#include "runner.h"
#include "killer.h"
#include "child.h"
#include "logger.h"


void init_result(struct result *_result) {
    _result->result = _result->error = SUCCESS;
    _result->cpu_time = _result->real_time = _result->signal = _result->exit_code = 0;
    _result->memory = 0;
}


static int64_t elapsed_milliseconds(const struct timespec *start,
                                    const struct timespec *end) {
    int64_t seconds = (int64_t) end->tv_sec - (int64_t) start->tv_sec;
    int64_t nanoseconds = (int64_t) end->tv_nsec - (int64_t) start->tv_nsec;
    return seconds * 1000 + nanoseconds / 1000000;
}


static int64_t process_group_cpu_milliseconds(pid_t process_group,
                                                int64_t *descendant_time) {
    DIR *proc = opendir("/proc");
    if (proc == NULL) {
        return -1;
    }
    long clock_ticks = sysconf(_SC_CLK_TCK);
    if (clock_ticks < 1) {
        closedir(proc);
        return -1;
    }

    uint64_t total_ticks = 0;
    uint64_t descendant_ticks = 0;
    struct dirent *entry;
    while ((entry = readdir(proc)) != NULL) {
        if (!isdigit((unsigned char) entry->d_name[0])) {
            continue;
        }
        char stat_path[PATH_MAX];
        int length = snprintf(stat_path, sizeof(stat_path),
                              "/proc/%s/stat", entry->d_name);
        if (length < 0 || (size_t) length >= sizeof(stat_path)) {
            continue;
        }
        FILE *stat_file = fopen(stat_path, "re");
        if (stat_file == NULL) {
            continue;
        }
        char stat_line[4096];
        if (fgets(stat_line, sizeof(stat_line), stat_file) == NULL) {
            fclose(stat_file);
            continue;
        }
        fclose(stat_file);

        char *fields = strrchr(stat_line, ')');
        if (fields == NULL || fields[1] != ' ') {
            continue;
        }
        fields += 2;
        char *save = NULL;
        char *token = strtok_r(fields, " ", &save);
        int field_index = 0;
        long parsed_group = -1;
        uint64_t times[4] = {0, 0, 0, 0};
        while (token != NULL && field_index <= 14) {
            if (field_index == 2) {
                parsed_group = strtol(token, NULL, 10);
            }
            else if (field_index >= 11 && field_index <= 14) {
                times[field_index - 11] = strtoull(token, NULL, 10);
            }
            token = strtok_r(NULL, " ", &save);
            field_index++;
        }
        if (parsed_group == process_group) {
            uint64_t own_ticks = times[0] + times[1];
            uint64_t reaped_child_ticks = times[2] + times[3];
            total_ticks += own_ticks + reaped_child_ticks;
            descendant_ticks += reaped_child_ticks;
            if (strtol(entry->d_name, NULL, 10) != process_group) {
                descendant_ticks += own_ticks;
            }
        }
    }
    closedir(proc);
    if (descendant_time != NULL) {
        *descendant_time =
            (int64_t) ((descendant_ticks * 1000U) / (uint64_t) clock_ticks);
    }
    return (int64_t) ((total_ticks * 1000U) / (uint64_t) clock_ticks);
}


static int wait_for_child_exit(pid_t child_pid, int max_cpu_time,
                               int max_real_time, const struct timespec *start,
                               struct timespec *end, bool *cpu_timed_out,
                               bool *real_timed_out, int64_t *observed_cpu_time) {
    const struct timespec poll_interval = {.tv_sec = 0, .tv_nsec = 2000000L};

    for (;;) {
        siginfo_t child_info;
        memset(&child_info, 0, sizeof(child_info));
        if (waitid(P_PID, (id_t) child_pid, &child_info,
                   WEXITED | WNOHANG | WNOWAIT) != 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        int64_t descendant_cpu_time = 0;
        int64_t group_cpu_time =
            process_group_cpu_milliseconds(child_pid, &descendant_cpu_time);
        if (group_cpu_time > *observed_cpu_time) {
            *observed_cpu_time = group_cpu_time;
        }
        bool exited_normally = child_info.si_pid == child_pid &&
                               child_info.si_code == CLD_EXITED &&
                               child_info.si_status == 0;
        if (max_cpu_time != UNLIMITED && group_cpu_time >= max_cpu_time &&
            (!exited_normally || descendant_cpu_time >= max_cpu_time)) {
            *cpu_timed_out = true;
            (void) kill_process_group(child_pid);
            if (child_info.si_pid != child_pid) {
                do {
                    memset(&child_info, 0, sizeof(child_info));
                } while (waitid(P_PID, (id_t) child_pid, &child_info,
                                WEXITED | WNOWAIT) != 0 && errno == EINTR);
            }
            if (child_info.si_pid != child_pid) {
                return -1;
            }
            return clock_gettime(CLOCK_MONOTONIC, end);
        }
        if (child_info.si_pid == child_pid) {
            return clock_gettime(CLOCK_MONOTONIC, end);
        }

        struct timespec now;
        if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
            return -1;
        }
        if (max_real_time != UNLIMITED &&
            elapsed_milliseconds(start, &now) >= max_real_time) {
            *real_timed_out = true;
            (void) kill_process_group(child_pid);
            do {
                memset(&child_info, 0, sizeof(child_info));
            } while (waitid(P_PID, (id_t) child_pid, &child_info,
                            WEXITED | WNOWAIT) != 0 && errno == EINTR);
            if (child_info.si_pid != child_pid) {
                return -1;
            }
            return clock_gettime(CLOCK_MONOTONIC, end);
        }

        struct timespec remaining = poll_interval;
        while (nanosleep(&remaining, &remaining) != 0 && errno == EINTR) {
        }
    }
}


static void add_timeval(struct timeval *total, const struct timeval *value) {
    total->tv_sec += value->tv_sec;
    total->tv_usec += value->tv_usec;
    if (total->tv_usec >= 1000000) {
        total->tv_sec += total->tv_usec / 1000000;
        total->tv_usec %= 1000000;
    }
}


static void merge_rusage(struct rusage *total, const struct rusage *value) {
    if (total == NULL) {
        return;
    }
    add_timeval(&total->ru_utime, &value->ru_utime);
    add_timeval(&total->ru_stime, &value->ru_stime);
    if (value->ru_maxrss > total->ru_maxrss) {
        total->ru_maxrss = value->ru_maxrss;
    }
}


static void reap_process_group(pid_t process_group, struct rusage *aggregate) {
    int status;
    for (;;) {
        struct rusage usage;
        pid_t reaped = wait4(-process_group, &status, 0, &usage);
        if (reaped > 0) {
            merge_rusage(aggregate, &usage);
            continue;
        }
        if (reaped < 0 && errno == EINTR) {
            continue;
        }
        return;
    }
}


static bool kill_adopted_children(void) {
    char children_path[64];
    snprintf(children_path, sizeof(children_path),
             "/proc/self/task/%ld/children", (long) getpid());
    FILE *children = fopen(children_path, "re");
    if (children == NULL) {
        return false;
    }

    bool found = false;
    long child;
    while (fscanf(children, "%ld", &child) == 1) {
        if (child > 0) {
            found = true;
            (void) kill((pid_t) child, SIGKILL);
        }
    }
    fclose(children);
    return found;
}


static void reap_adopted_descendants(struct rusage *aggregate) {
    const struct timespec pause = {.tv_sec = 0, .tv_nsec = 10000000L};
    for (int attempt = 0; attempt < 100; attempt++) {
        bool found = kill_adopted_children();
        int status;
        pid_t reaped;
        do {
            struct rusage usage;
            reaped = wait4(-1, &status, WNOHANG, &usage);
            if (reaped > 0) {
                found = true;
                merge_rusage(aggregate, &usage);
            }
        } while (reaped > 0);
        if (reaped < 0 && errno == ECHILD) {
            return;
        }
        if (!found) {
            return;
        }
        nanosleep(&pause, NULL);
    }
}


static void terminate_and_reap(pid_t child_pid, bool child_observed) {
    (void) kill_process_group(child_pid);
    if (!child_observed) {
        int status;
        while (waitpid(child_pid, &status, 0) < 0 && errno == EINTR) {
        }
    }
    reap_process_group(child_pid, NULL);
    reap_adopted_descendants(NULL);
}


static ssize_t read_child_error(int fd, struct child_error *child_error_info) {
    char *bytes = (char *) child_error_info;
    size_t received = 0;
    while (received < sizeof(*child_error_info)) {
        ssize_t read_size = read(fd, bytes + received, sizeof(*child_error_info) - received);
        if (read_size > 0) {
            received += (size_t) read_size;
        }
        else if (read_size == 0) {
            break;
        }
        else if (errno != EINTR) {
            return -1;
        }
    }
    return (ssize_t) received;
}


static bool requires_scoped_cwd(const char *rule_name) {
    if (rule_name == NULL) {
        return false;
    }
    return strcmp(rule_name, "c_cpp_file_io") == 0 ||
           strcmp(rule_name, "general_file_io") == 0 ||
           strcmp(rule_name, "golang_file_io") == 0 ||
           strcmp(rule_name, "node_file_io") == 0 ||
           strcmp(rule_name, "java") == 0 ||
           strcmp(rule_name, "java_file_io") == 0;
}


static bool is_sandbox_profile(const char *rule_name) {
    return rule_name != NULL &&
           (strcmp(rule_name, "c_cpp") == 0 || requires_scoped_cwd(rule_name) ||
            strcmp(rule_name, "general") == 0 ||
            strcmp(rule_name, "golang") == 0 ||
            strcmp(rule_name, "node") == 0);
}


void run(struct config *_config, struct result *_result) {
    FILE *log_fp = log_open(_config->log_path);
    init_result(_result);

    if (getuid() != 0) {
        ERROR_EXIT(ROOT_REQUIRED);
    }

    if ((_config->max_cpu_time < 1 && _config->max_cpu_time != UNLIMITED) ||
        (_config->max_real_time < 1 && _config->max_real_time != UNLIMITED) ||
        (_config->max_stack < 1) ||
        (_config->max_memory < 1 && _config->max_memory != UNLIMITED) ||
        (_config->max_process_number < 1 && _config->max_process_number != UNLIMITED) ||
        (_config->max_output_size < 1 && _config->max_output_size != UNLIMITED) ||
        _config->uid == (uid_t) -1 || _config->gid == (gid_t) -1 ||
        (requires_scoped_cwd(_config->seccomp_rule_name) && _config->cwd == NULL) ||
        (is_sandbox_profile(_config->seccomp_rule_name) &&
         (_config->uid == 0 || _config->gid == 0))) {
        ERROR_EXIT(INVALID_CONFIG);
    }

    if (prctl(PR_SET_CHILD_SUBREAPER, 1) != 0) {
        ERROR_EXIT(PROCESS_GROUP_FAILED);
    }

    int error_pipe[2];
    if (pipe2(error_pipe, O_CLOEXEC) != 0) {
        ERROR_EXIT(PIPE_FAILED);
    }

    struct timespec start;
    if (clock_gettime(CLOCK_MONOTONIC, &start) != 0) {
        close(error_pipe[0]);
        close(error_pipe[1]);
        ERROR_EXIT(WAIT_FAILED);
    }

    pid_t child_pid = fork();
    if (child_pid < 0) {
        close(error_pipe[0]);
        close(error_pipe[1]);
        ERROR_EXIT(FORK_FAILED);
    }
    if (child_pid == 0) {
        close(error_pipe[0]);
        log_close(log_fp);
        child_process(error_pipe[1], _config);
        _exit(EXIT_FAILURE);
    }

    close(error_pipe[1]);
    if (setpgid(child_pid, child_pid) != 0 && errno != EACCES && errno != ESRCH) {
        close(error_pipe[0]);
        terminate_and_reap(child_pid, false);
        ERROR_EXIT(PROCESS_GROUP_FAILED);
    }

    struct timespec end;
    bool cpu_timed_out = false;
    bool real_timed_out = false;
    int64_t observed_cpu_time = 0;
    if (wait_for_child_exit(child_pid, _config->max_cpu_time,
                            _config->max_real_time, &start, &end,
                            &cpu_timed_out, &real_timed_out,
                            &observed_cpu_time) != 0) {
        close(error_pipe[0]);
        terminate_and_reap(child_pid, false);
        ERROR_EXIT(WAIT_FAILED);
    }

    // The leader is still a zombie because waitid used WNOWAIT. Its PID/PGID
    // therefore cannot be reused while we terminate the complete process group.
    (void) kill_process_group(child_pid);

    int status;
    struct rusage resource_usage;
    pid_t wait_result;
    do {
        wait_result = wait4(child_pid, &status, 0, &resource_usage);
    } while (wait_result < 0 && errno == EINTR);
    if (wait_result < 0) {
        close(error_pipe[0]);
        reap_process_group(child_pid, NULL);
        ERROR_EXIT(WAIT_FAILED);
    }
    reap_process_group(child_pid, &resource_usage);
    reap_adopted_descendants(&resource_usage);

    int64_t real_time = elapsed_milliseconds(&start, &end);
    if (real_time < 0) {
        real_time = 0;
    }
    if (real_time > INT32_MAX) {
        real_time = INT32_MAX;
    }
    _result->real_time = (int) real_time;
    int64_t cpu_microseconds =
        ((int64_t) resource_usage.ru_utime.tv_sec +
         (int64_t) resource_usage.ru_stime.tv_sec) * 1000000 +
        (int64_t) resource_usage.ru_utime.tv_usec +
        (int64_t) resource_usage.ru_stime.tv_usec;
    int64_t cpu_milliseconds = cpu_microseconds / 1000;
    if (observed_cpu_time > cpu_milliseconds) {
        cpu_milliseconds = observed_cpu_time;
    }
    if (cpu_milliseconds > INT32_MAX) {
        cpu_milliseconds = INT32_MAX;
    }
    _result->cpu_time = (int) cpu_milliseconds;
    _result->memory = resource_usage.ru_maxrss * 1024;

    struct child_error child_error_info;
    ssize_t error_size = read_child_error(error_pipe[0], &child_error_info);
    close(error_pipe[0]);

    if (error_size == (ssize_t) sizeof(child_error_info)) {
        _result->result = SYSTEM_ERROR;
        _result->error = child_error_info.error;
        LOG_FATAL(log_fp, "Error: System errno: %s; Internal errno: %d",
                  strerror(child_error_info.system_errno), child_error_info.error);
        log_close(log_fp);
        return;
    }
    if (error_size != 0) {
        _result->result = SYSTEM_ERROR;
        _result->error = PIPE_FAILED;
        LOG_FATAL(log_fp, "Error: incomplete child error record");
        log_close(log_fp);
        return;
    }

    if (WIFSIGNALED(status)) {
        _result->signal = WTERMSIG(status);
        _result->result = RUNTIME_ERROR;
    }
    else if (WIFEXITED(status)) {
        _result->exit_code = WEXITSTATUS(status);
        if (_result->exit_code != 0) {
            _result->result = RUNTIME_ERROR;
        }
    }

    if (_config->max_memory != UNLIMITED && _result->memory > _config->max_memory) {
        _result->result = MEMORY_LIMIT_EXCEEDED;
    }
    if (real_timed_out) {
        if (_result->real_time < _config->max_real_time) {
            _result->real_time = _config->max_real_time;
        }
        _result->result = REAL_TIME_LIMIT_EXCEEDED;
    }
    else if (cpu_timed_out) {
        if (_result->cpu_time < _config->max_cpu_time) {
            _result->cpu_time = _config->max_cpu_time;
        }
        _result->result = CPU_TIME_LIMIT_EXCEEDED;
    }
    else if (_config->max_cpu_time != UNLIMITED &&
             _result->cpu_time >= _config->max_cpu_time &&
             (_result->signal == SIGKILL || _result->signal == SIGXCPU)) {
        _result->result = CPU_TIME_LIMIT_EXCEEDED;
    }

    log_close(log_fp);
}
