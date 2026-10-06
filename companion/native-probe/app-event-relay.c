/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Guest-loopback owned event receiver; no filesystem reads or host listener.
 */
#include "../app-probe/EventRecord.h"
#include "../app-probe/LoopbackEvent.h"
extern int printf(const char *,...),fflush(void *),inferno_owned_process(int);
extern unsigned alarm(unsigned);
static unsigned number(char **p,unsigned maximum,int *valid) {
    unsigned n=0,digits=0;
    while(**p>='0' && **p<='9') {unsigned d=*(*p)++-'0';if(d>maximum || n>(maximum-d)/10) {*valid=0;return 0;}n=n*10+d;digits++;}
    if(!digits || n>maximum)*valid=0;return n;
}
static int token(char **p,char *out,unsigned size) {
    unsigned n=0;while(**p && **p!=' ') {if(n+1>=size)return -1;out[n++]=*(*p)++;}
    out[n]=0;if(**p!=' ')return -1;(*p)++;return 0;
}
static struct {unsigned pid,last;} seen[32];
static unsigned used,relayed;
static int record(char *p,const char *boot) {
    const char *raw=p;
    char magic[24],record_boot[37],event[32];int valid=1;
    if(token(&p,magic,sizeof(magic)) || strcmp(magic,"INFERNO_EVENT_V1") || token(&p,record_boot,sizeof(record_boot)) || strcmp(record_boot,boot))return 1;
    unsigned pid=number(&p,2147483647,&valid);if(!valid || *p++!=' ')return 2;
    unsigned sequence=number(&p,64,&valid);if(!valid || !pid || !sequence || *p++!=' ')return 3;
    if(token(&p,event,sizeof(event)) || !inferno_event_name(event))return 4;
    unsigned count=number(&p,1000000,&valid);if(!valid || *p)return 5;
    if(!inferno_owned_process((int)pid))return 6;
    unsigned slot=0;while(slot<used && seen[slot].pid!=pid)slot++;
    if(slot==used) {if(used==32)return 7;seen[used++].pid=pid;}
    if(sequence<=seen[slot].last)return 8;
    seen[slot].last=sequence;
    printf("INFERNO_EVENT_RELAY_RAW source=guest-loopback record=%s\n",raw);
    printf("INFERNO_EVENT_RELAY_RECORD boot=%s pid=%u sequence=%u source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0\n",boot,pid,sequence);
    printf("INFERNO_UIKIT_PROBE_V1 event=%s count=%u\n",event,count);fflush(0);relayed++;return 0;
}
int inferno_app_event_watch(void) {
    char boot[37];alarm(7200);
    if(inferno_boot_uuid(boot)) {printf("INFERNO_EVENT_RELAY_ERROR stage=boot-identity errno=%d\n",inferno_boot_query_errno);fflush(0);return 1;}
    const char *failed_stage="socket";
    int listener=socket(2,1,0),error=0,one=1;
    if(listener<0) {error=*__error();goto failed;}
    failed_stage="nonblocking";if(inferno_nonblocking(listener)) {error=*__error();goto failed;}
    failed_stage="reuse-address";if(setsockopt(listener,0xffff,4,&one,sizeof(one))) {error=*__error();goto failed;}
    struct inferno_loopback_address address=inferno_loopback_address();
    failed_stage="bind-loopback";if(bind(listener,&address,sizeof(address))) {error=*__error();goto failed;}
    failed_stage="listen";if(listen(listener,4)) {error=*__error();goto failed;}
    printf("INFERNO_EVENT_RELAY_READY boot=%s lifetime=7200 transport=tcp address=127.0.0.1 port=37373 connections_max=64\n",boot);fflush(0);
    unsigned connections=0,errors=0;
    while(connections<64 && relayed<512) {
        struct inferno_pollfd pending={listener,1,0};int ready=poll(&pending,1,1000);
        if(ready<0) {if(*__error()==4)continue;error=*__error();break;}
        if(!ready)continue;
        if(!(pending.revents&1)) {error=5;break;}
        int fd=accept(listener,0,0);
        if(fd<0) {if(*__error()==35 || *__error()==4)continue;error=*__error();break;}
        connections++;
        int outcome=20,connection_errno=0;char line[192];unsigned length=0;
        if(inferno_nonblocking(fd)) {connection_errno=*__error();outcome=21;}
        else for(unsigned attempt=0;attempt<8;attempt++) {
            struct inferno_pollfd readable={fd,1,0};int n=poll(&readable,1,250);
            if(n<0) {if(*__error()==4)continue;connection_errno=*__error();outcome=22;break;}
            if(!n)continue;
            long got=recv(fd,line+length,sizeof(line)-1-length,0);
            if(got<0) {if(*__error()==4 || *__error()==35)continue;connection_errno=*__error();outcome=23;break;}
            if(!got) {outcome=24;break;}
            unsigned old=length;length+=(unsigned)got;int complete=0;
            for(unsigned i=old;i<length;i++) {
                if(!line[i]) {outcome=25;complete=1;break;}
                if(line[i]=='\n') {line[i]=0;outcome=i+1==length?record(line,boot):26;complete=1;break;}
            }
            if(complete)break;
            if(length==sizeof(line)-1) {outcome=27;break;}
        }
        close(fd);
        if(outcome && errors++<16) {printf("INFERNO_EVENT_RELAY_REJECT result=%d errno=%d connection=%u\n",outcome,connection_errno,connections);fflush(0);}
    }
    close(listener);printf("INFERNO_EVENT_RELAY_END relayed=%u connections=%u errno=%d\n",relayed,connections,error);fflush(0);return error?1:0;
failed:
    if(listener>=0)close(listener);printf("INFERNO_EVENT_RELAY_ERROR stage=%s errno=%d\n",failed_stage,error);fflush(0);return 1;
}
