/* Owned fixed-path byte patcher for a disposable APFS copy. No Apple source. */
typedef unsigned long size_t;
typedef unsigned long long u64;
typedef unsigned int u32;
typedef unsigned char u8;
extern int printf(const char *, ...), fflush(void *), strcmp(const char *, const char *);
extern int open(const char *, int, ...), close(int), fsync(int), unmount(const char *, int);
extern long read(int, void *, size_t), pread(int, void *, size_t, long long), pwrite(int, const void *, size_t, long long);
extern long long lseek(int, long long, int);
extern int access(const char *, int), fork(void), execve(const char *, char *const[], char *const[]), waitpid(int, int *, int), *__error(void);
extern void _exit(int), sync(void);
extern unsigned int sleep(unsigned int);
extern void *malloc(size_t);
extern void free(void *);
#define CACHE "/mnt1/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e"
#define PLAN "/usr/share/inferno-cache.patch"
#define DIGESTS "/usr/share/inferno-cache.sha256"
#define MAX_PLAN (16U*1024*1024)
#define MAX_RECORDS 65536U
#define MAX_RECORD 4096U
static u32 le32(const u8 *p) { return (u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24; }
static u64 le64(const u8 *p) { return le32(p)|(u64)le32(p+4)<<32; }
static int equal(const u8 *a,const u8 *b,size_t n) { for(size_t i=0;i<n;i++) if(a[i]!=b[i]) return 0;return 1; }
static u32 rr(u32 x,unsigned n) { return x>>n|x<<(32-n); }
struct sha { u32 h[8]; u8 b[64]; u64 count; unsigned used; };
static const u32 k[64]={
0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static void sha_block(struct sha *s) {
 u32 w[64];for(unsigned i=0;i<16;i++){const u8*p=s->b+i*4;w[i]=(u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}
 for(unsigned i=16;i<64;i++){u32 a=w[i-15],b=w[i-2];w[i]=w[i-16]+(rr(a,7)^rr(a,18)^(a>>3))+w[i-7]+(rr(b,17)^rr(b,19)^(b>>10));}
 u32 a=s->h[0],b=s->h[1],c=s->h[2],d=s->h[3],e=s->h[4],f=s->h[5],g=s->h[6],h=s->h[7];
 for(unsigned i=0;i<64;i++){u32 t=h+(rr(e,6)^rr(e,11)^rr(e,25))+((e&f)^(~e&g))+k[i]+w[i];u32 u=(rr(a,2)^rr(a,13)^rr(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+t;d=c;c=b;b=a;a=t+u;}
 s->h[0]+=a;s->h[1]+=b;s->h[2]+=c;s->h[3]+=d;s->h[4]+=e;s->h[5]+=f;s->h[6]+=g;s->h[7]+=h;
}
static void sha_init(struct sha*s){u32 v[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};for(unsigned i=0;i<8;i++)s->h[i]=v[i];s->count=0;s->used=0;}
static void sha_add(struct sha*s,const u8*p,size_t n){s->count+=n;for(size_t i=0;i<n;i++){s->b[s->used++]=p[i];if(s->used==64){sha_block(s);s->used=0;}}}
static void sha_end(struct sha*s,u8*out){u64 bits=s->count*8;u8 one=128,zero=0;sha_add(s,&one,1);while(s->used!=56)sha_add(s,&zero,1);u8 tail[8];for(unsigned i=0;i<8;i++)tail[7-i]=bits>>(8*i);sha_add(s,tail,8);for(unsigned i=0;i<32;i++)out[i]=s->h[i/4]>>(24-8*(i%4));}
static int hash_file(int fd,u64 size,u8 out[32]){struct sha s;sha_init(&s);u8 b[65536];u64 off=0;while(off<size){size_t want=size-off<sizeof(b)?size-off:sizeof(b);long n=pread(fd,b,want,off);if(n<0&&*__error()==4)continue;if(n<=0)return -1;sha_add(&s,b,n);off+=n;}sha_end(&s,out);return 0;}
static void print_hash(const char*stage,const u8 h[32]){printf("INFERNO_CACHE_SHA256 %s ",stage);for(unsigned i=0;i<32;i++)printf("%02x",h[i]);printf("\n");fflush(0);}
static int exact(int fd,u8*p,size_t n,u64 offset,int writing){size_t done=0;while(done<n){long r=writing?pwrite(fd,p+done,n-done,offset+done):pread(fd,p+done,n-done,offset+done);if(r<0&&*__error()==4)continue;if(r<=0)return -1;done+=r;}return 0;}
static int mount_system(void){char*args[]={"/sbin/mount_apfs","/dev/disk0s1s1","/mnt1",0};int pid=fork();if(pid==0){char*env[]={"PATH=/usr/bin:/bin:/usr/sbin:/sbin",0};execve(args[0],args,env);_exit(127);}if(pid<0)return -1;int st=-1;while(waitpid(pid,&st,0)<0)if(*__error()!=4)return -1;printf("INFERNO_CACHE_MOUNT status=%d\n",st);fflush(0);return st;}
#ifndef HASH_SELFTEST
int main(int argc,char**argv){
 int status=2,planfd=-1,digestfd=-1,cachefd=-1,mounted=0;u8*plan=0;u8 expected[64],hash[32],check[MAX_RECORD];
 if(argc!=2||strcmp(argv[1],"--disposable-root-copy"))return 2;
 printf("INFERNO_CACHE_BEGIN fixed_path=%s\n",CACHE);fflush(0);
 planfd=open(PLAN,0);digestfd=open(DIGESTS,0);if(planfd<0||digestfd<0)goto done;
 long long plen=lseek(planfd,0,2);if(plen<24||plen>MAX_PLAN||lseek(digestfd,0,2)!=64)goto done;
 plan=malloc(plen);if(!plan||exact(planfd,plan,plen,0,0)||exact(digestfd,expected,64,0,0))goto done;
 if(!equal(plan,(const u8*)"INFRPAT1",8)||le32(plan+20))goto done;
 u64 size=le64(plan+8);u32 count=le32(plan+16);if(!size||size>8ULL*1024*1024*1024||!count||count>MAX_RECORDS)goto done;
 size_t pos=24;u64 last=0;
 for(u32 i=0;i<count;i++){if((size_t)plen-pos<16)goto done;u64 off=le64(plan+pos);u32 n=le32(plan+pos+8);if(le32(plan+pos+12)||!n||n>MAX_RECORD||off<last||off>size||n>size-off)goto done;pos+=16;if((size_t)plen-pos<2ULL*n)goto done;last=off+n;pos+=2*n;}
 if(pos!=(size_t)plen)goto done;
 for(int i=0;access("/dev/disk0s1s1",0)&&i<30;i++)sleep(1);
 status=3;if(access("/dev/disk0s1s1",0)||mount_system())goto done;mounted=1;
 /* O_RDWR | O_NOFOLLOW: fixed final component must not be a symlink. */
 cachefd=open(CACHE,2|0x100);status=4;if(cachefd<0||lseek(cachefd,0,2)!=(long long)size)goto done;
 status=5;if(hash_file(cachefd,size,hash))goto done;print_hash("before",hash);if(!equal(hash,expected,32))goto done;
 pos=24;status=6;
 for(u32 i=0;i<count;i++){u64 off=le64(plan+pos);u32 n=le32(plan+pos+8);pos+=16;if(exact(cachefd,check,n,off,0)||!equal(check,plan+pos,n)){printf("INFERNO_CACHE_OLD_MISMATCH record=%u offset=%llu\n",i,off);goto done;}pos+=2*n;}
 printf("INFERNO_CACHE_VALIDATED bytes=%llu records=%u\n",size,count);fflush(0);
 pos=24;status=7;
 for(u32 i=0;i<count;i++){u64 off=le64(plan+pos);u32 n=le32(plan+pos+8);pos+=16;if(exact(cachefd,plan+pos+n,n,off,1))goto done;pos+=2*n;}
 status=8;if(fsync(cachefd))goto done;
 pos=24;status=9;
 for(u32 i=0;i<count;i++){u64 off=le64(plan+pos);u32 n=le32(plan+pos+8);pos+=16;if(exact(cachefd,check,n,off,0)||!equal(check,plan+pos+n,n))goto done;pos+=2*n;}
 status=10;if(lseek(cachefd,0,2)!=(long long)size||hash_file(cachefd,size,hash))goto done;print_hash("after",hash);if(!equal(hash,expected+32,32))goto done;status=0;
 done:
 if(cachefd>=0&&close(cachefd)&&!status)status=11;
 if(planfd>=0)close(planfd);if(digestfd>=0)close(digestfd);if(plan)free(plan);
 sync();if(mounted){int r=unmount("/mnt1",0);printf("INFERNO_CACHE_UNMOUNT status=%d errno=%d\n",r,*__error());if(r&&!status)status=12;}
 printf("INFERNO_CACHE_RESULT status=%d\n",status);fflush(0);return status;
}
#else
int main(void){u8 h[32];struct sha s;sha_init(&s);sha_add(&s,(const u8*)"abc",3);sha_end(&s,h);print_hash("abc",h);sha_init(&s);sha_end(&s,h);print_hash("empty",h);return 0;}
#endif
