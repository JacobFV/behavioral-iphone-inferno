// SPDX-License-Identifier: AGPL-3.0-or-later
// Self-authored narrow Darwin clock/dispatch declarations, no SDK implementation.
#ifndef INFERNO_OWNED_CLOCK_H
#define INFERNO_OWNED_CLOCK_H
struct inferno_timebase { unsigned numer,denom; };
_Static_assert(sizeof(struct inferno_timebase)==8,"Darwin mach_timebase_info ABI");
extern unsigned long long mach_absolute_time(void);
extern int mach_timebase_info(struct inferno_timebase *);
extern char _dispatch_main_q;
extern void dispatch_async_f(void *,void *,void (*)(void *));
extern void dispatch_after_f(unsigned long long,void *,void *,void (*)(void *));
extern unsigned long long dispatch_time(unsigned long long,long long);
static inline int inferno_timing_hook(const char *s) {
    return !strcmp(s,"main")?1:!strcmp(s,"launch-delegate")?2:
           !strcmp(s,"window-request")?4:!strcmp(s,"appeared")?8:
           !strcmp(s,"active")?16:0;
}
#endif
