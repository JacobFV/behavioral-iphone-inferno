/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Explicit, bounded original-tool diagnosis of two fixed system executables.
 * No signals to targets, grants, arbitrary argv/PIDs, or automatic samples.
 */
#include "sample-control.h"
#include "open-control.h"
#include "../app-probe/EventRecord.h"
#include "../app-probe/OwnedClock.h"
extern int printf(const char *,...),snprintf(char *,unsigned long,const char *,...),fflush(void *);
extern int proc_listpids(unsigned,unsigned,void *,int),proc_pidpath(int,void *,unsigned),proc_pidinfo(int,int,unsigned long long,void *,int);
extern int pipe(int *),fcntl(int,int,...),fork(void),dup2(int,int),close(int),execve(const char *,char *const[],char *const[]);
extern int waitpid(int,int *,int),kill(int,int),usleep(unsigned);
extern long read(int,void *,unsigned long);
extern void _exit(int);
struct short_info {unsigned pid,ppid,pgid,status;char comm[16];unsigned flags,uid,gid,ruid,rgid,svuid,svgid,reserved;};
struct unique_info {unsigned char uuid[16];unsigned long long unique,parent;int version;unsigned reserved;unsigned long long reserved2,reserved3;};
_Static_assert(sizeof(struct short_info)==64,"Original proc short info");
_Static_assert(sizeof(struct unique_info)==56,"Original proc unique info");
static const char *paths[]={"/System/Library/CoreServices/SpringBoard.app/SpringBoard","/usr/libexec/backboardd"};
static const char *names[]={"SPRINGBOARD","BACKBOARDD"};
static int enabled,console_fd=-1,child=-1,output_fd=-1,target_pid,target_index;
static int reaped,raw_status,eof,read_error,killed,truncated,output_error,wait_error,finished;
static unsigned attempts,byte_count,chunks;
static char boot[37],request_id[33];
static struct unique_info original;
static struct inferno_timebase base;
static unsigned long long began,killed_at;
static int starts(const char *s,const char *p) {while(*p)if(*s++!=*p++)return 0;return 1;}
static int expired(unsigned long long start,unsigned seconds) {return (mach_absolute_time()-start)/base.denom>=(unsigned long long)seconds*1000000000ULL/base.numer;}
static int identity(int pid,int target,struct unique_info *u) {
    char path[4096]={0};struct short_info b={0};
    int n=proc_pidpath(pid,path,sizeof(path));if(n<=0 || n>=(int)sizeof(path) || strcmp(path,paths[target]))return 0;
    n=proc_pidinfo(pid,13,0,&b,sizeof(b));if(n!=sizeof(b)||b.pid!=(unsigned)pid||b.uid!=501)return 0;
    n=proc_pidinfo(pid,17,0,u,sizeof(*u));return n==sizeof(*u) && u->unique;
}
static int resolve(int target,struct unique_info *u) {
    int pids[1024]={0};int n=proc_listpids(1,0,pids,sizeof(pids));
    if(n<=0||n>=(int)sizeof(pids)||n%(int)sizeof(int))return -1;
    int found=0;struct unique_info candidate;
    for(unsigned i=0;i<(unsigned)n/sizeof(int);i++)if(pids[i]>0 && identity(pids[i],target,&candidate)) {
        if(found)return -2;found=pids[i];*u=candidate;
    }
    return found;
}
static int same_target(void) {struct unique_info u={0};return identity(target_pid,target_index,&u) && u.unique==original.unique && u.version==original.version;}
static void signal_child(const char *reason) {
    if(child<=0||reaped||killed)return;
    int status=0,r=waitpid(child,&status,1);
    if(r==child){reaped=1;raw_status=status;return;}
    if(r<0){if(*__error()==4)return;wait_error=*__error();printf("INFERNO_SAMPLE_WAIT_ERROR request_id=%s errno=%d no_signal_sent=1\n",request_id,*__error());fflush(0);enabled=0;return;}
    /* waitpid==0: only this still-unreaped child may be signalled. */
    r=kill(child,9);int e=r?*__error():0;killed=1;killed_at=mach_absolute_time();
    printf("INFERNO_SAMPLE_CHILD_STOP request_id=%s reason=%s child=%d result=%d errno=%d guest_ticks=%llu\n",request_id,reason,child,r,e,killed_at);fflush(0);
}
static void drain(void) {
    for(unsigned i=0;i<16 && output_fd>=0 && !eof;i++) {
        unsigned char data[256];unsigned remaining=262144-byte_count;
        if(!remaining){truncated=1;signal_child("output_limit");close(output_fd);output_fd=-1;break;}
        unsigned cap=remaining<sizeof(data)?remaining:sizeof(data);long n=read(output_fd,data,cap);
        if(!n){eof=1;close(output_fd);output_fd=-1;break;}
        if(n<0){int e=*__error();if(e==4)continue;if(e==35)break;read_error=e;close(output_fd);output_fd=-1;signal_child("read_error");break;}
        char hex[513];static const char digits[]="0123456789abcdef";
        for(long k=0;k<n;k++){hex[2*k]=digits[data[k]>>4];hex[2*k+1]=digits[data[k]&15];}hex[2*n]=0;
        int r=printf("INFERNO_SAMPLE_DATA request_id=%s offset=%u bytes=%ld hex=%s\n",request_id,byte_count,n,hex);
        if(r<0||fflush(0)){output_error=1;enabled=0;signal_child("console_error");}
        byte_count+=(unsigned)n;chunks++;
        if(output_error)break;
    }
}
static void finish(void) {
    if(finished)return;finished=1;
    int match=same_target();
    int complete=reaped && raw_status==0 && !wait_error && eof && !truncated && !read_error && !output_error && !killed && match;
    printf("INFERNO_SAMPLE_END request_id=%s boot=%s target=%s pid=%d unique=%llu idversion=%d bytes=%u chunks=%u eof=%d truncated=%d read_errno=%d output_error=%d reaped=%d raw_status=%d wait_errno=%d killed=%d target_post_match=%d complete=%d guest_ticks=%llu pid_reuse_atomicity=unproven\n",request_id,boot,names[target_index],target_pid,original.unique,original.version,byte_count,chunks,eof,truncated,read_error,output_error,reaped,raw_status,wait_error,killed,match,complete,mach_absolute_time());fflush(0);
    if(output_fd>=0)close(output_fd);output_fd=-1;
    if(reaped)child=-1;else enabled=0; /* Never reuse an unreaped child slot. */
}
void inferno_sample_start(int fd) {
    console_fd=fd;enabled=!inferno_boot_uuid(boot)&&!mach_timebase_info(&base)&&base.numer&&base.denom;
    printf("INFERNO_SAMPLE_READY enabled=%d boot=%s max_requests=2 targets=SPRINGBOARD,BACKBOARDD automatic_sample=0\n",enabled,enabled?boot:"unavailable");fflush(0);
}
int inferno_sample_busy(void) {return child>0;}
void inferno_sample_poll(void) {
    if(child<=0)return;
    drain();
    if(!reaped && !wait_error){int r=waitpid(child,&raw_status,1);if(r==child)reaped=1;else if(r<0&&*__error()!=4){enabled=0;wait_error=*__error();}}
    if(finished){if(reaped)child=-1;return;}
    if(reaped && (eof || output_fd<0)){finish();return;}
    if(!killed && expired(began,60)) {
        if(reaped || wait_error){truncated=1;finish();return;}
        signal_child("guest_deadline");
    }
    if(killed && expired(killed_at,5)) {
        if(output_fd>=0){close(output_fd);output_fd=-1;truncated=1;}
        if(reaped)finish();else {enabled=0;finish();} /* poll/reap, no further signal or command */
    }
}
int inferno_sample_handle(const char *line) {
    if(!starts(line,"INFERNO_SAMPLE_V1"))return 0;
    char id[33]={0},uuid[37]={0};const char *reason=0;int target=-1;
    if(!starts(line,"INFERNO_SAMPLE_V1 "))reason="syntax";
    else {
        const char *p=line+18;
        for(unsigned i=0;i<32;i++){char c=*p;if(!c||!((c>='0'&&c<='9')||(c>='a'&&c<='f'))){reason="syntax";break;}id[i]=c;p++;}
        if(!reason){if(*p++!=' ')reason="syntax";else for(unsigned i=0;i<36;i++){if(!*p){reason="syntax";break;}uuid[i]=*p++;}}
        if(!reason){if(*p++!=' ')reason="syntax";else if(!strcmp(p,names[0]))target=0;else if(!strcmp(p,names[1]))target=1;else reason="target";}
    }
    if(!reason && !enabled)reason="disabled";
    if(!reason && strcmp(uuid,boot))reason="foreign_boot";
    if(!reason && (child>0||inferno_open_busy()))reason="busy";
    if(!reason && attempts>=2)reason="limit";
    if(!reason && inferno_command_id_seen(id))reason="duplicate";
    if(reason){printf("INFERNO_SAMPLE_REJECT reason=%s\n",reason);fflush(0);return -1;}
    attempts++;inferno_command_id_remember(id);for(unsigned i=0;i<33;i++)request_id[i]=id[i];target_index=target;
    *__error()=0;target_pid=resolve(target,&original);int e=*__error();
    printf("INFERNO_SAMPLE_REQUEST request_id=%s boot=%s target=%s pid=%d resolve_errno=%d guest_ticks=%llu\n",id,boot,names[target],target_pid,e,mach_absolute_time());fflush(0);
    if(target_pid<=0 || !same_target()){printf("INFERNO_SAMPLE_FAILED request_id=%s stage=target_resolution\n",id);fflush(0);return -1;}
    int fds[2];if(pipe(fds)){printf("INFERNO_SAMPLE_FAILED request_id=%s stage=pipe errno=%d\n",id,*__error());fflush(0);return -1;}
    int flags=fcntl(fds[0],3);if(flags<0||fcntl(fds[0],4,flags|4)){e=*__error();close(fds[0]);close(fds[1]);printf("INFERNO_SAMPLE_FAILED request_id=%s stage=nonblocking errno=%d\n",id,e);fflush(0);return -1;}
    char pid_arg[24];snprintf(pid_arg,sizeof(pid_arg),"%d",target_pid);
    if(!same_target()){close(fds[0]);close(fds[1]);printf("INFERNO_SAMPLE_FAILED request_id=%s stage=target_revalidation\n",id);fflush(0);return -1;}
    printf("INFERNO_SAMPLE_BEGIN request_id=%s target=%s pid=%d uid=501 unique=%llu idversion=%d output_cap=262144 guest_deadline_seconds=60 original_tool=/usr/sbin/spindump target_signals=0\n",id,names[target],target_pid,original.unique,original.version);fflush(0);
    child=fork();
    if(child==0) {
        close(fds[0]);if(dup2(fds[1],1)<0||dup2(fds[1],2)<0)_exit(126);if(fds[1]>2)close(fds[1]);
        if(console_fd>2)close(console_fd);close(0);
        char *args[]={"/usr/sbin/spindump",pid_arg,"2","100","-onlyTarget","-noBinary","-noFile","-stdout","-noSymbolicate","-timelimit","20",0};
        char *env[]={"PATH=/usr/bin:/bin:/usr/sbin:/sbin","HOME=/var/root","TMPDIR=/var/tmp",0};execve(args[0],args,env);_exit(127);
    }
    e=child<0?*__error():0;close(fds[1]);
    if(child<0){close(fds[0]);printf("INFERNO_SAMPLE_FAILED request_id=%s stage=fork errno=%d\n",id,e);fflush(0);return -1;}
    output_fd=fds[0];began=mach_absolute_time();byte_count=chunks=0;reaped=raw_status=eof=read_error=killed=truncated=output_error=wait_error=finished=0;return 1;
}
void inferno_sample_close(void) {
    if(child<=0)return;
    signal_child("helper_cleanup");for(unsigned i=0;i<50 && child>0;i++){inferno_sample_poll();if(child>0)usleep(100000);}
    if(child>0){if(output_fd>=0){close(output_fd);output_fd=-1;}truncated=1;finish();}
}
