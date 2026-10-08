/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Owned fixed-file, read-only original-System cache inspector. */
typedef unsigned long size_t;
typedef unsigned long long u64;
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
extern int printf(const char *, ...), fflush(void *), strcmp(const char *, const char *);
extern int open(const char *, int, ...), close(int), unmount(const char *, int);
extern long pread(int, void *, size_t, long long), write(int, const void *, size_t);
extern int access(const char *, int), fork(void), execve(const char *, char *const[], char *const[]), waitpid(int, int *, int), *__error(void);
extern void _exit(int);
extern unsigned int sleep(unsigned int);
struct file_stat { int dev; u16 mode,nlink; u64 ino; u32 uid,gid; int rdev; long long times[8],size,blocks; int blksize; u32 flags,gen; int spare; long long qspare[2]; };
_Static_assert(sizeof(struct file_stat)==144,"Darwin stat64 ABI");
extern int lstat(const char *,struct file_stat *), fstat(int,struct file_stat *);
#include "sha256.h"
#define LAUNCHD "/mnt1/System/Library/xpc/launchd.plist"
#define DYLD "/mnt1/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e"
static int same(const struct file_stat*a,const struct file_stat*b){return a->dev==b->dev&&a->ino==b->ino&&a->size==b->size&&a->mode==b->mode&&a->uid==b->uid&&a->gid==b->gid&&a->times[2]==b->times[2]&&a->times[3]==b->times[3]&&a->times[4]==b->times[4]&&a->times[5]==b->times[5];}
static int mount_system(void){char*args[]={"/sbin/mount_apfs","-o","ro","/dev/disk0s1s1","/mnt1",0};int pid=fork();if(pid==0){char*env[]={"PATH=/usr/bin:/bin:/usr/sbin:/sbin",0};execve(args[0],args,env);_exit(127);}if(pid<0)return -1;int status=-1;while(waitpid(pid,&status,0)<0)if(*__error()!=4)return -1;printf("INFERNO_INSPECT_MOUNT status=%d mode=ro\n",status);fflush(0);return status;}
static int emit_hex(u64 offset,const u8*bytes,size_t n){
 static const char hex[]="0123456789abcdef";char line[1025];
 if(n>512)return -1;
 if(printf("INFERNO_INSPECT_DATA name=launchd offset=%llu bytes=%lu hex=",offset,n)<0||fflush(0))return -1;
 for(size_t i=0;i<n;i++){line[2*i]=hex[bytes[i]>>4];line[2*i+1]=hex[bytes[i]&15];}line[2*n]='\n';
 size_t done=0,total=2*n+1;while(done<total){long k=write(1,line+done,total-done);if(k<0&&*__error()==4)continue;if(k<=0)return -1;done+=k;}return 0;
}
static int inspect(const char*name,const char*path,int exporting){
 int fd=-1,status=1;struct file_stat a,b,c;u8 bytes[65536],digest[32];struct sha hash;u64 offset=0;
 if(lstat(path,&a)||(a.mode&0xf000)!=0x8000||a.size<=0||a.uid!=0)return 1;
 if((exporting&&a.size>2*1024*1024)||(!exporting&&a.size!=2052489216LL))return 2;
 fd=open(path,0x100);if(fd<0)return 3;/* O_RDONLY|O_NOFOLLOW */
 if(fstat(fd,&b)||!same(&a,&b))goto done;
 printf("INFERNO_INSPECT_FILE name=%s bytes=%llu mode=%u uid=%u gid=%u\n",name,(u64)a.size,(u32)a.mode,a.uid,a.gid);fflush(0);sha_init(&hash);
 while(offset<(u64)a.size){size_t cap=exporting?512:sizeof(bytes);size_t want=(u64)a.size-offset<cap?(size_t)((u64)a.size-offset):cap;long n=pread(fd,bytes,want,offset);if(n<0&&*__error()==4)continue;if(n<=0||(size_t)n>want)goto done;sha_add(&hash,bytes,n);if(exporting&&emit_hex(offset,bytes,n))goto done;offset+=n;}
 if(pread(fd,bytes,1,offset)!=0||fstat(fd,&c)||!same(&b,&c)||lstat(path,&c)||!same(&b,&c))goto done;
 sha_end(&hash,digest);printf("INFERNO_INSPECT_HASH name=%s bytes=%llu sha256=",name,offset);for(unsigned i=0;i<32;i++)printf("%02x",digest[i]);printf("\n");fflush(0);status=0;
 done:if(close(fd)&&!status)status=4;return status;
}
int main(int argc,char**argv){
 int status=2,mounted=0;if(argc!=2||strcmp(argv[1],"--disposable-root-copy"))return 2;
 printf("INFERNO_INSPECT_BEGIN version=1 fixed_files=2\n");fflush(0);
 for(int i=0;access("/dev/disk0s1s1",0)&&i<30;i++)sleep(1);
 if(access("/dev/disk0s1s1",0)||mount_system())goto done;mounted=1;
 status=3;if(inspect("launchd",LAUNCHD,1))goto done;
 status=4;if(inspect("dyld",DYLD,0))goto done;status=0;
 done:if(mounted){int r=unmount("/mnt1",0);printf("INFERNO_INSPECT_UNMOUNT status=%d errno=%d\n",r,*__error());if(r&&!status)status=5;}
 printf("INFERNO_INSPECT_RESULT status=%d\n",status);fflush(0);return status;
}
