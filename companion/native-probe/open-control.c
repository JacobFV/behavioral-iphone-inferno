/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Sole-reader command demultiplexer. Fixed owned OPEN only; no app termination.
 */
#include "open-control.h"
#include "../app-probe/EventRecord.h"
#include "../app-probe/OwnedClock.h"
extern int printf(const char *,...),fflush(void *),fork(void),close(int),waitpid(int,int *,int),kill(int,int),usleep(unsigned);
extern int setgroups(int,const unsigned *),setgid(unsigned),setuid(unsigned),execve(const char *,char *const[],char *const[]);
extern void _exit(int);
static char boot[37],requests[8][33];
static unsigned request_count,all_count;
static char all_ids[40][33];
int inferno_command_id_seen(const char *id) {for(unsigned i=0;i<all_count;i++)if(!strcmp(id,all_ids[i]))return 1;return 0;}
void inferno_command_id_remember(const char *id) {if(all_count<40) {for(unsigned i=0;i<33;i++)all_ids[all_count][i]=id[i];all_count++;}}

static int enabled,console_fd=-1,child=-1,killed;
static unsigned long long began,killed_at;
static struct inferno_timebase base;
static int prefix(const char *s,const char *p) {while(*p)if(*s++!=*p++)return 0;return 1;}
static int parse_open(const char *line,char id[33],char uuid[37]) {
    if(!prefix(line,"INFERNO_OPEN_V1 "))return -1;
    const char *p=line+16;
    for(unsigned i=0;i<32;i++) {char c=*p++;if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return -1;id[i]=c;}
    id[32]=0;if(*p++!=' ')return -1;
    for(unsigned i=0;i<36;i++) {char c=*p++;if(!c)return -1;uuid[i]=c;}
    uuid[36]=0;return *p?-1:0;
}
static int expired(unsigned long long start,unsigned seconds) {
    unsigned long long delta=mach_absolute_time()-start;
    return delta/base.denom>=(unsigned long long)seconds*1000000000ULL/base.numer;
}
void inferno_open_start(int fd) {
    console_fd=fd;
    enabled=!inferno_boot_uuid(boot) && !mach_timebase_info(&base) && base.numer && base.denom;
    printf("INFERNO_OPEN_READY enabled=%d boot=%s max_requests=8 automatic_open=0\n",enabled,enabled?boot:"unavailable");fflush(0);
}
int inferno_open_busy(void) {return child>0;}
void inferno_open_poll(void) {
    if(child<=0)return;
    int status=0,result=waitpid(child,&status,1);
    if(result==child) {
        printf("INFERNO_OPEN_CHILD_END request_id=%s pid=%d raw_status=%d timed_out=%d completion_is_not_visual=1\n",requests[request_count-1],child,status,killed);fflush(0);child=-1;return;
    }
    if(result<0) {
        if(*__error()==4)return;
        printf("INFERNO_OPEN_CHILD_ERROR stage=wait errno=%d pid=%d no_signal_sent=1\n",*__error(),child);fflush(0);child=-1;enabled=0;return;
    }
    // waitpid==0 proves this still is our unreaped child; PID cannot be reused.
    if(!killed && expired(began,150)) {
        int r=kill(child,9),e=r?*__error():0;
        printf("INFERNO_OPEN_CHILD_TIMEOUT pid=%d signal_result=%d errno=%d\n",child,r,e);fflush(0);
        killed=1;killed_at=mach_absolute_time();
    } else if(killed==1 && expired(killed_at,5)) {
        printf("INFERNO_OPEN_CHILD_REAP_PENDING pid=%d further_commands_disabled=1\n",child);fflush(0);enabled=0;
        // Keep the child identity, poll only; never signal a reused PID or spawn another.
        killed=2;
    }
}
int inferno_open_handle(const char *line) {
    if(!prefix(line,"INFERNO_OPEN_V1"))return 0;
    char id[33],uuid[37];const char *reason=0;
    if(parse_open(line,id,uuid))reason="syntax";
    else if(!enabled)reason="disabled";
    else if(strcmp(uuid,boot))reason="foreign_boot";
    else if(child>0)reason="busy";
    else if(request_count==8)reason="limit";
    else if(inferno_command_id_seen(id))reason="duplicate";
    if(reason) {printf("INFERNO_OPEN_REJECT reason=%s\n",reason);fflush(0);return -1;}
    for(unsigned i=0;i<33;i++)requests[request_count][i]=id[i];request_count++;inferno_command_id_remember(id);
    printf("INFERNO_OPEN_REQUEST request_id=%s boot=%s timestamp=%llu\n",id,boot,mach_absolute_time());fflush(0);
    child=fork();
    if(child==0) {
        // No framework work, stdio, or shared locks between fork and exec.
        close(console_fd);if(console_fd!=0)close(0);
        if(setgroups(0,0)||setgid(501)||setuid(501))_exit(126);
        char *args[]={"/usr/bin/inferno-launcher","--open-only",id,0};
        char *env[]={"PATH=/usr/bin:/bin:/usr/sbin:/sbin","HOME=/var/mobile","CFFIXED_USER_HOME=/var/mobile","TMPDIR=/var/tmp",0};
        execve(args[0],args,env);_exit(127);
    }
    if(child<0) {printf("INFERNO_OPEN_FORK_ERROR request_id=%s errno=%d\n",id,*__error());fflush(0);return -1;}
    began=mach_absolute_time();killed=0;
    printf("INFERNO_OPEN_DISPATCHED request_id=%s child=%d accepted_by_os=unqueried\n",id,child);fflush(0);return 1;
}
void inferno_open_close(void) {
    if(child<=0)return;
    inferno_open_poll();
    if(child>0) {
        int status=0,result=waitpid(child,&status,1);
        if(result==0) {kill(child,9);for(unsigned i=0;i<50;i++) {result=waitpid(child,&status,1);if(result==child || (result<0 && *__error()!=4))break;usleep(100000);}}
        printf("INFERNO_OPEN_CLEANUP child=%d reap_result=%d raw_status=%d\n",child,result,status);fflush(0);
    }
}
