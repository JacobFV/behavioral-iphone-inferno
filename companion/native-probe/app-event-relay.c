/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Read only our fixed event file. A fresh exec child, never an input mechanism.
 */
#include "../app-probe/EventRecord.h"
extern int open(const char *,int,...),close(int),printf(const char *,...),fflush(void *),*__error(void);
extern long read(int,void *,unsigned long);
extern unsigned sleep(unsigned),alarm(unsigned);
static unsigned number(char **p,unsigned maximum,int *valid) {
    unsigned n=0,digits=0;
    while(**p>='0' && **p<='9') {unsigned d=*(*p)++-'0';if(n>(maximum-d)/10 || d>maximum) {*valid=0;return 0;}n=n*10+d;digits++;}
    if(!digits || n>maximum)*valid=0;
    return n;
}
static int token(char **p,char *out,unsigned size) {
    unsigned n=0;
    while(**p && **p!=' ') {if(n+1>=size)return -1;out[n++]=*(*p)++;}
    out[n]=0;if(**p!=' ')return -1;(*p)++;return 0;
}
extern int lstat(const char *,struct inferno_event_stat *);
static void path_diagnostics(void) {
    static const char *paths[]={"/var/mobile/Library/Caches",INFERNO_EVENT_PATH};
    static struct {int initialized,result,error;unsigned mode,uid,gid;unsigned long long ino;long long size;} previous[2];
    static unsigned reports;
    for(unsigned i=0;i<2 && reports<32;i++) {
        struct inferno_event_stat st={0};int result=lstat(paths[i],&st),error=result?*__error():0;
        if(!previous[i].initialized || result!=previous[i].result || error!=previous[i].error ||
           st.mode!=previous[i].mode || st.uid!=previous[i].uid || st.gid!=previous[i].gid || st.ino!=previous[i].ino || st.size!=previous[i].size) {
            printf("INFERNO_EVENT_PATH path=%s result=%d errno=%d mode=%o uid=%u gid=%u inode=%llu size=%lld\n",paths[i],result,error,st.mode,st.uid,st.gid,st.ino,st.size);fflush(0);reports++;
            previous[i].initialized=1;previous[i].result=result;previous[i].error=error;
            previous[i].mode=st.mode;previous[i].uid=st.uid;previous[i].gid=st.gid;previous[i].ino=st.ino;previous[i].size=st.size;
        }
    }
}
int inferno_app_event_watch(void) {
    char boot[37];
    alarm(7200);
    if(inferno_boot_uuid(boot)) {printf("INFERNO_EVENT_RELAY_ERROR stage=boot-identity errno=%d\n",*__error());fflush(0);return 1;}
    printf("INFERNO_EVENT_RELAY_READY boot=%s lifetime=7200 path=%s\n",boot,INFERNO_EVENT_PATH);fflush(0);
    struct {unsigned pid,last;} seen[32]={0};unsigned used=0,relayed=0,errors=0;
    for(unsigned seconds=0;seconds<7200 && relayed<512;seconds++) {
        path_diagnostics();
        int fd=open(INFERNO_EVENT_PATH,0x100); // RDONLY|NOFOLLOW
        if(fd<0) {
            if(*__error()!=2 && errors++<8) {printf("INFERNO_EVENT_RELAY_ERROR stage=open errno=%d\n",*__error());fflush(0);}
        } else {
            struct inferno_event_stat st;char data[INFERNO_EVENT_LIMIT+1];unsigned got=0;int good=1;
            if(fstat(fd,&st) || (st.mode&0170000)!=0100000 || st.uid!=501 || st.nlink!=1 || st.size<0 || st.size>INFERNO_EVENT_LIMIT)good=0;
            while(good && got<INFERNO_EVENT_LIMIT) {
                long n=read(fd,data+got,INFERNO_EVENT_LIMIT-got);
                if(n<0 && *__error()==4)continue;
                if(n<0) {good=0;break;}if(!n)break;got+=(unsigned)n;
            }
            close(fd);data[got]=0;
            if(!good && errors++<8) {printf("INFERNO_EVENT_RELAY_ERROR stage=read-or-file-identity errno=%d\n",*__error());fflush(0);}
            if(good) {
                unsigned start=0;
                for(unsigned i=0;i<got && relayed<512;i++)if(data[i]=='\n') {
                    data[i]=0;char *p=data+start;start=i+1;
                    char magic[24],record_boot[37],event[32];int valid=1;
                    if(token(&p,magic,sizeof(magic)) || strcmp(magic,"INFERNO_EVENT_V1") || token(&p,record_boot,sizeof(record_boot)) || strcmp(record_boot,boot))continue;
                    unsigned pid=number(&p,2147483647,&valid);if(!valid || *p++!=' ')continue;
                    unsigned sequence=number(&p,64,&valid);if(!valid || !pid || !sequence || *p++!=' ')continue;
                    if(token(&p,event,sizeof(event)) || !inferno_event_name(event))continue;
                    unsigned count=number(&p,1000000,&valid);if(!valid || *p)continue;
                    unsigned slot=0;while(slot<used && seen[slot].pid!=pid)slot++;
                    if(slot==used) {if(used==32)continue;seen[used++].pid=pid;}
                    if(sequence<=seen[slot].last)continue;
                    seen[slot].last=sequence;
                    printf("INFERNO_EVENT_RELAY_RECORD boot=%s pid=%u sequence=%u source=owned-file\n",boot,pid,sequence);
                    printf("INFERNO_UIKIT_PROBE_V1 event=%s count=%u\n",event,count);fflush(0);relayed++;
                }
            }
        }
        unsigned remaining=1;while(remaining)remaining=sleep(remaining);
    }
    printf("INFERNO_EVENT_RELAY_END relayed=%u\n",relayed);fflush(0);return 0;
}
