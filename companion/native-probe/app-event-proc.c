/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Original libproc queries, restricted to the claimed owned executable and UID.
 */
extern int proc_pidpath(int,void *,unsigned);
extern int proc_pidinfo(int,int,unsigned long long,void *,int);
extern int strcmp(const char *,const char *),snprintf(char *,unsigned long,const char *,...);
extern int printf(const char *,...),fflush(void *),*__error(void);
struct inferno_bsd_short {
    unsigned pid,ppid,pgid,status;char comm[16];
    unsigned flags,uid,gid,ruid,rgid,svuid,svgid,reserved;
};
int inferno_owned_process(int pid) {
    char executable[4096]={0};struct inferno_bsd_short info={0};
    int n=proc_pidpath(pid,executable,sizeof(executable));
    if(n<=0 || n>=(int)sizeof(executable) || strcmp(executable,"/Applications/InfernoProbe.app/InfernoProbe"))return 0;
    n=proc_pidinfo(pid,13,0,&info,sizeof(info));
    static unsigned errors;
    if(n!=sizeof(info) && errors++<8) {printf("INFERNO_EVENT_PROC_ERROR stage=owned-shortbsd pid=%d result=%d errno=%d\n",pid,n,n<=0?*__error():0);fflush(0);}
    return n==sizeof(info) && info.pid==(unsigned)pid && info.uid==501;
}
struct inferno_proc_unique {
    unsigned char uuid[16];
    unsigned long long unique,parent;
    int version;unsigned reserved;
    unsigned long long reserved2,reserved3;
};
_Static_assert(sizeof(struct inferno_proc_unique)==56,"Original Darwin proc unique info");
int inferno_owned_incarnation(int pid,unsigned long long *unique,int *version,int *error) {
    struct inferno_proc_unique info={0};
    int n=proc_pidinfo(pid,17,0,&info,sizeof(info));
    *error=n==0?*__error():0;
    *unique=n==sizeof(info)?info.unique:0;*version=n==sizeof(info)?info.version:0;
    return n;
}
