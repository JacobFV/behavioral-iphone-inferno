/* Owned console command reader. No shell, replay, or automatic gesture. */
#include "hid-input.h"
#include "open-control.h"
#include "sample-control.h"
extern int printf(const char *,...),fflush(void *),open(const char *,int,...),close(int),*__error(void),strcmp(const char *,const char *);
extern long read(int,void *,unsigned long);
extern int usleep(unsigned);
extern unsigned alarm(unsigned);
extern unsigned long long mach_absolute_time(void);
struct timebase {unsigned numer,denom;};
extern int mach_timebase_info(struct timebase *);
extern void (*signal(int,void (*)(int)))(int);
extern void *dlopen(const char *,int),*dlsym(void *,const char *);
static unsigned (*notify_register_read)(const char *,int *),(*notify_check_read)(int,int *),(*notify_cancel_read)(int);
static int readiness_token=-1,readiness_poll_enabled;
static unsigned readiness_observations;
static void readiness_watch_start(void) {
    void *lib=dlopen("/usr/lib/system/libsystem_notify.dylib",2);
    if(lib) {
        *(void **)(&notify_register_read)=dlsym(lib,"notify_register_check");
        *(void **)(&notify_check_read)=dlsym(lib,"notify_check");
        *(void **)(&notify_cancel_read)=dlsym(lib,"notify_cancel");
    }
    if(!notify_register_read || !notify_check_read || !notify_cancel_read) {
        printf("INFERNO_HID_SETUP_WATCH result=symbols_unavailable\n");fflush(0);return;
    }
    unsigned status=notify_register_read("com.apple.purplebuddy.readytoexit",&readiness_token);
    int initial=0;unsigned clear_status=status?status:notify_check_read(readiness_token,&initial);
    readiness_poll_enabled=!status && !clear_status;
    printf("INFERNO_HID_SETUP_WATCH register_status=%u initial_clear_status=%u initial_check=%d initial_is_not_event=1 timestamp=%llu\n",status,clear_status,initial,mach_absolute_time());fflush(0);
    if(status)readiness_token=-1;
}
static void readiness_watch_poll(const char *phase) {
    if(!readiness_poll_enabled)return;
    int changed=0;unsigned status=notify_check_read(readiness_token,&changed);
    if(status || changed) {
        if(readiness_observations++<64)
            printf("INFERNO_HID_SETUP_NOTIFICATION phase=%s check_status=%u changed=%d timestamp=%llu readiness_state=unqueried\n",phase,status,changed,mach_absolute_time());
        fflush(0);
    }
    if(status)readiness_poll_enabled=0;
}
static volatile int stopping;
static void stop(int sig) {(void)sig;stopping=1;}
int inferno_hid_stopping(void) {return stopping;}
static int word(const char **cursor,const char *expected) {
    const char *p=*cursor;
    while(*expected)if(*p++!=*expected++)return -1;
    if(*p!=' ')return -1;
    *cursor=p+1;return 0;
}
static int number(const char **cursor,unsigned *out,int last) {
    const char *p=*cursor;unsigned n=0,digits=0;
    while(*p>='0' && *p<='9') {
        if(++digits>5)return -1;
        n=n*10+(unsigned)(*p++-'0');
    }
    if(!digits || (last?*p!=0:*p!=' '))return -1;
    *cursor=p+(last?0:1);*out=n;return 0;
}
static int parse(const char *line,struct inferno_gesture *g) {
    const char *p=line;
    if(word(&p,"INFERNO_HID_V1"))return -1;
    for(unsigned i=0;i<32;i++) {
        char c=*p++;
        if(!((c>='0' && c<='9') || (c>='a' && c<='f')))return -1;
        g->request_id[i]=c;
    }
    g->request_id[32]=0;
    if(*p++!=' ')return -1;
    if(!word(&p,"TAP"))g->swipe=0;
    else if(!word(&p,"SWIPE"))g->swipe=1;
    else return -1;
    if(number(&p,&g->x0,0) || number(&p,&g->y0,0))return -1;
    if(g->swipe) {
        if(number(&p,&g->x1,0) || number(&p,&g->y1,0))return -1;
    } else {g->x1=g->x0;g->y1=g->y0;}
    if(number(&p,&g->duration_ms,1))return -1;
    return g->x0>32767 || g->x1>32767 || g->y0>32767 || g->y1>32767 || !g->duration_ms || g->duration_ms>2000 ? -1:0;
}
static int handle(const char *line,char seen[INFERNO_HID_MAX_REQUESTS][33],unsigned *count) {
    struct inferno_gesture g;
    if(parse(line,&g)) {printf("INFERNO_HID_REJECT reason=syntax_or_bounds\n");fflush(0);return -1;}
    if(inferno_command_id_seen(g.request_id)) {
        printf("INFERNO_HID_REJECT request_id=%s reason=duplicate\n",g.request_id);fflush(0);return -1;
    }
    if(*count>=INFERNO_HID_MAX_REQUESTS)return -1;
    for(unsigned i=0;i<33;i++)seen[*count][i]=g.request_id[i];
    ++*count;inferno_command_id_remember(g.request_id);
    printf("INFERNO_HID_REQUEST request_id=%s kind=%s x0=%u y0=%u x1=%u y1=%u duration_ms=%u timestamp=%llu\n",g.request_id,g.swipe?"SWIPE":"TAP",g.x0,g.y0,g.x1,g.y1,g.duration_ms,mach_absolute_time());fflush(0);
    readiness_watch_poll("before_gesture");
    int status=inferno_hid_dispatch(&g);
    readiness_watch_poll("after_gesture");
    printf("INFERNO_HID_ACK request_id=%s attempt_status=%d delivery=unproven timestamp=%llu\n",g.request_id,status,mach_absolute_time());fflush(0);
    return status;
}
#ifdef INFERNO_HID_TRANSPORT_ONLY
int inferno_hid_dispatch(const struct inferno_gesture *g) {(void)g;return -100;}
void inferno_hid_close(void) {}
int inferno_hid_prepare(void) {return -100;}
#endif
int main(int argc,char **argv) {
    if(argc!=2 || strcmp(argv[1],"--console-operator-input"))return 64;
    struct timebase tb;
    if(mach_timebase_info(&tb) || !tb.numer || !tb.denom)return 65;
    signal(2,stop);signal(15,stop);signal(14,stop);alarm(INFERNO_HID_LIFETIME_SECONDS);
    int fd=open("/dev/console",4); /* Darwin O_RDONLY | O_NONBLOCK; leave termios unchanged. */
    if(fd<0){printf("INFERNO_HID_OPEN_FAILED errno=%d\n",*__error());fflush(0);return 66;}
    printf("INFERNO_HID_BEGIN automatic_gestures=0\n");fflush(0);
    inferno_open_start(fd);
    inferno_sample_start(fd);
    readiness_watch_start();
    int backend=inferno_hid_prepare();
    printf("INFERNO_HID_BACKEND_INITIALIZE status=%d delivery=unproven\n",backend);fflush(0);
    printf("INFERNO_HID_READY protocol=1 console=/dev/console max_requests=%u lifetime_seconds=%u automatic_gestures=0\n",INFERNO_HID_MAX_REQUESTS,INFERNO_HID_LIFETIME_SECONDS);fflush(0);
    static char seen[INFERNO_HID_MAX_REQUESTS][33];
    char line[160];unsigned used=0,count=0,rejected=0;int discard=0;
    unsigned long long began=mach_absolute_time();
    while(!stopping && count<INFERNO_HID_MAX_REQUESTS && rejected<32) {
        inferno_open_poll();
        inferno_sample_poll();
        readiness_watch_poll("idle");
        unsigned long long ticks=mach_absolute_time()-began;
        if((ticks/(unsigned long long)tb.denom)*tb.numer>=INFERNO_HID_LIFETIME_SECONDS*1000000000ULL)break;
        char buffer[128];long got=read(fd,buffer,sizeof(buffer));
        if(got<0) {if(*__error()!=35 && *__error()!=4)break;usleep(100000);continue;}
        if(!got)break;
        for(long i=0;i<got && !stopping && count<INFERNO_HID_MAX_REQUESTS && rejected<32;i++) {
            unsigned char c=(unsigned char)buffer[i];
            if(c=='\n') {
                if(discard){printf("INFERNO_HID_REJECT reason=line_encoding_or_length\n");fflush(0);rejected++;}
                else {line[used]=0;int control=inferno_sample_handle(line);if(!control)control=inferno_open_handle(line);if(control<0)rejected++;else if(!control) {if(inferno_open_busy() || inferno_sample_busy()) {printf("INFERNO_HID_REJECT reason=control_child_busy\n");fflush(0);rejected++;}else if(handle(line,seen,&count))rejected++;}}
                used=0;discard=0;
            } else if(c<32 || c>126 || used>=sizeof(line)-1)discard=1;
            else if(!discard)line[used++]=(char)c;
        }
    }
    if(readiness_token>=0 && notify_cancel_read)notify_cancel_read(readiness_token);
    inferno_sample_close();inferno_open_close();inferno_hid_close();close(fd);printf("INFERNO_HID_EXIT requests=%u rejected=%u stop=%d\n",count,rejected,stopping);fflush(0);return 0;
}
