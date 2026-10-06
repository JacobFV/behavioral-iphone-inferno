/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Owned one-shot app staging helper. Original guest mount/copyfile implement IO.
 * Requires a disposable copy of prepared21; never edits an existing fixture.
 */
typedef unsigned long size_t;
typedef unsigned int u32;
typedef unsigned short u16;
extern int printf(const char *, ...), fflush(void *), strcmp(const char *, const char *);
extern int fork(void), execve(const char *, char *const[], char *const[]), waitpid(int,int*,int);
extern void _exit(int), sync(void);
extern int access(const char *,int), mkdir(const char *,u16), unmount(const char *,int);
extern int chmod(const char *,u16), chown(const char *,u32,u32), *__error(void);
extern int copyfile(const char *,const char *,void *,u32), open(const char *,int,...), close(int);
extern long read(int,void *,size_t);
extern unsigned int sleep(unsigned int);
struct attrs { u16 count,reserved; u32 common,volume,directory,file,fork; };
struct volname { u32 size; int offset; u32 length; char text[1024]; };
extern int getattrlist(const char *,struct attrs *,void *,size_t,unsigned long);
struct fs { u32 bsize; int iosize; unsigned long long blocks,bfree,bavail,files,ffree;
 int fsid[2]; u32 owner,type,flags,subtype; char typename[16],on[1024],from[1024]; u32 ext,reserved[7]; };
extern int statfs(const char *,struct fs *);
_Static_assert(sizeof(struct fs)==2168,"Darwin statfs64 ABI");
static int run(char *const a[]) {
 printf("INFERNO_STAGE_EXEC"); for(int i=0;a[i];++i) printf(" %s",a[i]); printf("\n");fflush(0);
 int pid=fork(),status=-1;
 if(!pid){char *env[]={"PATH=/usr/bin:/bin:/usr/sbin:/sbin",0};execve(a[0],a,env);_exit(127);}
 if(pid<0)return -1;
 while(waitpid(pid,&status,0)<0)if(*__error()!=4)return -1;
 printf("INFERNO_STAGE_STATUS raw=%d\n",status);fflush(0);return status;
}
static int same(const char *source,const char *dest) {
 int a=open(source,0),b=open(dest,0),ok=a>=0&&b>=0; unsigned long long bytes=0;
 unsigned char left[4096],right[4096];
 while(ok){long n=read(a,left,sizeof(left));if(n<0){ok=0;break;}long total=0;
  while(total<n){long m=read(b,right+total,n-total);if(m<=0){ok=0;break;}total+=m;}
  if(!ok)break;for(long i=0;i<n;++i)if(left[i]!=right[i])ok=0;
  bytes+=n;if(!n){if(read(b,right,1)!=0)ok=0;break;}}
 if(a>=0)close(a);if(b>=0)close(b);
 printf("INFERNO_STAGE_COMPARE %s bytes=%llu equal=%d\n",dest,bytes,ok);fflush(0);return ok?0:-1;
}
static int copy(const char *src,const char *dst,u16 mode) {
 if(access(dst,0)==0){printf("INFERNO_STAGE_REFUSE_EXISTING %s\n",dst);fflush(0);return -1;}
 if(copyfile(src,dst,0,15|(1<<17)|(1<<18)|(1<<19)) || chmod(dst,mode) || chown(dst,0,0))return -1;
 return same(src,dst);
}
int main(int argc,char **argv) {
 if(argc!=2||strcmp(argv[1],"--disposable-app-stage"))return 64;
 int system=0,data=0,result=1;struct fs fs;
 printf("INFERNO_STAGE_BEGIN\n");fflush(0);
 for(int i=0;access("/dev/disk0s1s2",0)&&i<30;++i)sleep(1);
 char *mountsys[]={"/sbin/mount_apfs","-o","rw","/dev/disk0s1s1","/mnt1",0};
 if(run(mountsys))goto done;system=1;
 if(statfs("/mnt1",&fs))goto done;
 printf("INFERNO_STAGE_SYSTEM_MOUNT flags=0x%x device=%s\n",fs.flags,fs.from);fflush(0);
 if((fs.flags&1)||access("/mnt1/System/Library/CoreServices/SystemVersion.plist",0))goto done;
 char *mountdata[]={"/sbin/mount_apfs","-o","rw","/dev/disk0s1s2","/mnt2",0};
 if(run(mountdata))goto done;data=1;
 struct attrs attr={5,0,0,0x80002000,0,0,0};struct volname name={0};
 if(getattrlist("/mnt2",&attr,&name,sizeof(name),0)||name.offset<8||
    (unsigned long)name.offset+4+name.length>sizeof(name)||!name.length)goto done;
 char *vol=(char *)&name.offset+name.offset;
 if(vol[name.length-1]||strcmp(vol,"Data"))goto done;
 if(statfs("/mnt2",&fs)||(fs.flags&1))goto done;
 printf("INFERNO_STAGE_DATA_MOUNT name=%s flags=0x%x device=%s\n",vol,fs.flags,fs.from);fflush(0);
 if(mkdir("/mnt2/inferno",0755)||chown("/mnt2/inferno",0,0))goto done;
 if(mkdir("/mnt2/inferno/InfernoProbe.app",0755)||chown("/mnt2/inferno/InfernoProbe.app",0,0))goto done;
 if(copy("/usr/share/inferno-stage-app","/mnt2/inferno/InfernoProbe.app/InfernoProbe",0755)||
    copy("/usr/share/inferno-stage-info","/mnt2/inferno/InfernoProbe.app/Info.plist",0644)||
    copy("/usr/share/inferno-stage-launcher","/mnt2/inferno/inferno-launcher",0755)||
    copy("/usr/share/inferno-stage-job","/mnt1/System/Library/LaunchDaemons/org.inferno.app-probe.plist",0644))goto done;
 result=0;
done:
 printf("INFERNO_STAGE_COPY_RESULT result=%d errno=%d\n",result,*__error());fflush(0);sync();
 if(data){int r=unmount("/mnt2",0);printf("INFERNO_STAGE_UNMOUNT data=%d errno=%d\n",r,*__error());if(r)result=2;}
 if(system){int r=unmount("/mnt1",0);printf("INFERNO_STAGE_UNMOUNT system=%d errno=%d\n",r,*__error());if(r)result=2;}
 printf("INFERNO_STAGE_DONE result=%d\n",result);fflush(0);return result;
}
