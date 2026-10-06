/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Original libproc queries, restricted to the owned executable's vnode metadata.
 */
extern int proc_listpids(unsigned,unsigned,void *,int);
extern int proc_pidpath(int,void *,unsigned);
extern int proc_pidinfo(int,int,unsigned long long,void *,int);
extern int proc_pidfdinfo(int,int,int,void *,int);
extern int strcmp(const char *,const char *),snprintf(char *,unsigned long,const char *,...);
extern int printf(const char *,...),fflush(void *),*__error(void);
struct inferno_bsd_short {
    unsigned pid,ppid,pgid,status;char comm[16];
    unsigned flags,uid,gid,ruid,rgid,svuid,svgid,reserved;
};
struct inferno_fd {int fd;unsigned type;};
struct inferno_vinfo_stat {
    unsigned dev;unsigned short mode,nlink;unsigned long long ino;
    unsigned uid,gid;long long times[8],size,blocks;
    int blksize;unsigned flags,gen,rdev;long long spare[2];
};
struct inferno_vnode_path {
    unsigned openflags,status;long long offset;int type;unsigned guardflags;
    struct inferno_vinfo_stat stat;int vnode_type,pad;int fsid[2];char path[1024];
};
_Static_assert(sizeof(struct inferno_bsd_short)==64,"original shortbsd ABI");
_Static_assert(__builtin_offsetof(struct inferno_bsd_short,uid)==36,"original shortbsd uid");
_Static_assert(sizeof(struct inferno_vinfo_stat)==136,"original vinfo stat ABI");
_Static_assert(sizeof(struct inferno_vnode_path)==1200,"original vnode path ABI");
_Static_assert(__builtin_offsetof(struct inferno_vnode_path,path)==176,"original vnode path offset");
static int owned_process(int pid) {
    char executable[4096]={0};struct inferno_bsd_short info={0};
    int n=proc_pidpath(pid,executable,sizeof(executable));
    if(n<=0 || n>=(int)sizeof(executable) || strcmp(executable,"/Applications/InfernoProbe.app/InfernoProbe"))return 0;
    n=proc_pidinfo(pid,13,0,&info,sizeof(info));
    static unsigned errors;
    if(n!=sizeof(info) && errors++<8) {printf("INFERNO_EVENT_PROC_ERROR stage=owned-shortbsd pid=%d result=%d errno=%d\n",pid,n,n<=0?*__error():0);fflush(0);}
    return n==sizeof(info) && info.pid==(unsigned)pid && info.uid==501;
}
int inferno_proc_event_path(char *output,unsigned long capacity,unsigned *device,unsigned long long *inode) {
    int pids[512]={0};static unsigned reports;int candidates=0;
    int n=proc_listpids(4,501,pids,sizeof(pids));
    if(n<=0 || n>(int)sizeof(pids) || n%(int)sizeof(int)) {if(reports++<16) {printf("INFERNO_EVENT_PROC_ERROR stage=list-pids result=%d errno=%d\n",n,n<=0?*__error():0);fflush(0);}return 10;}
    for(int i=0;i<n/(int)sizeof(int);i++) {
        int pid=pids[i];if(pid<=0 || !owned_process(pid))continue;
        if(++candidates>4)break;
        struct inferno_fd fds[128];int bytes=proc_pidinfo(pid,1,0,fds,sizeof(fds));
        if(reports++<16) {printf("INFERNO_EVENT_PROC pid=%d uid=501 exact_executable=1 fd_bytes=%d errno=%d\n",pid,bytes,bytes<=0?*__error():0);fflush(0);}
        if(bytes<=0 || bytes>(int)sizeof(fds) || bytes%(int)sizeof(fds[0]))continue;
        for(int j=0;j<bytes/(int)sizeof(fds[0]);j++) {
            if(fds[j].type!=1 || fds[j].fd<0)continue;
            struct inferno_vnode_path vnode={0};
            int size=proc_pidfdinfo(pid,fds[j].fd,2,&vnode,sizeof(vnode));
            if(size!=sizeof(vnode)) {if(reports++<16) {printf("INFERNO_EVENT_PROC_ERROR stage=vnode-path pid=%d fd=%d result=%d errno=%d\n",pid,fds[j].fd,size,size<=0?*__error():0);fflush(0);}continue;}
            unsigned length=0;while(length<sizeof(vnode.path) && vnode.path[length])length++;
            if(!length || length>=sizeof(vnode.path) || vnode.path[0]!='/')continue;
            const char *basename=vnode.path;
            for(unsigned k=0;k<length;k++)if(vnode.path[k]=='/')basename=vnode.path+k+1;
            if(strcmp(basename,"org.inferno.companion.probe.events") || vnode.stat.uid!=501 ||
               (vnode.stat.mode&0170000)!=0100000 || vnode.stat.nlink!=1 || vnode.stat.size<0 || vnode.stat.size>16384)continue;
            if(!owned_process(pid))return 11;
            int written=snprintf(output,capacity,"%s",vnode.path);
            if(written<=0 || (unsigned long)written>=capacity)return 12;
            *device=vnode.stat.dev;*inode=vnode.stat.ino;
            printf("INFERNO_EVENT_PROC_FOUND pid=%d fd=%d inode=%llu uid=%u path=%s\n",pid,fds[j].fd,vnode.stat.ino,vnode.stat.uid,output);fflush(0);
            return 0;
        }
    }
    return candidates?14:13;
}
