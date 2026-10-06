/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Owned diagnostic: original guest execve after dropping to mobile credentials.
 * No launch privileges, registration workaround or file writes.
 */
extern int printf(const char *,...),fflush(void *),fork(void),waitpid(int,int*,int);
extern int setgroups(int,const unsigned int *),setgid(unsigned int),setuid(unsigned int);
extern unsigned int getuid(void),getgid(void),sleep(unsigned int);
extern int strcmp(const char*,const char*);
extern int kill(int,int),access(const char *,int),open(const char *,int,...),close(int);
extern long read(int,void*,unsigned long);
extern int execve(const char *,char *const[],char *const[]),*__error(void);
extern void _exit(int);
static int attempt(char *path,int mobile,int noargs,const char *label){
 int timeout=noargs?60:150;
 printf("INFERNO_EXEC_WRAPPER_BEGIN case=%s path=%s watchdog=%d uid=%u gid=%u\n",label,path,timeout,getuid(),getgid());fflush(0);
 int pid=fork();
 if(!pid){
  if(mobile && (setgroups(0,0)||setgid(501)||setuid(501))){
   printf("INFERNO_EXEC_WRAPPER_CREDENTIALS_FAILED errno=%d\n",*__error());fflush(0);_exit(126);
  }
  printf("INFERNO_EXEC_WRAPPER_CHILD uid=%u gid=%u\n",getuid(),getgid());fflush(0);
  *__error()=0;int console_fd=open("/dev/console",1),console_errno=*__error();
  printf("INFERNO_EXEC_WRAPPER_CONSOLE_OPEN fd=%d errno=%d uid=%u gid=%u\n",console_fd,console_errno,getuid(),getgid());fflush(0);if(console_fd>=0)close(console_fd);
  char *argv[]={path,"/private/var/inferno/InfernoProbe.app","org.inferno.companion.probe",0};
  if(noargs)argv[1]=0;
  char *env[]={"PATH=/usr/bin:/bin:/usr/sbin:/sbin","HOME=/var/mobile","CFFIXED_USER_HOME=/var/mobile","TMPDIR=/var/tmp",0};
  *__error()=0;int xr=access(argv[0],1),xe=*__error();
  *__error()=0;int rr=access(argv[0],4),re=*__error();
  *__error()=0;int fd=open(argv[0],0),oe=*__error();long bytes=-1;int be=0;char header[16384];
  if(fd>=0){bytes=0;while(bytes<16384){*__error()=0;long n=read(fd,header+bytes,16384-(unsigned long)bytes);be=*__error();if(n<=0)break;bytes+=n;}close(fd);}
  printf("INFERNO_EXEC_WRAPPER_ACCESS x=%d xerrno=%d r=%d rerrno=%d fd=%d open_errno=%d read_bytes=%ld read_errno=%d\n",xr,xe,rr,re,fd,oe,bytes,be);fflush(0);
  execve(argv[0],argv,env);
  printf("INFERNO_EXEC_WRAPPER_EXEC_FAILED errno=%d uid=%u gid=%u\n",*__error(),getuid(),getgid());fflush(0);_exit(127);
 }
 if(pid<0){printf("INFERNO_EXEC_WRAPPER_FORK_FAILED errno=%d\n",*__error());fflush(0);return 1;}
 int status=-1,done=0;
 for(int seconds=0;seconds<timeout;seconds++){
  int result=waitpid(pid,&status,1); /* Darwin WNOHANG */
  if(result==pid){done=1;break;}
  if(result<0 && *__error()!=4){printf("INFERNO_EXEC_WRAPPER_WAIT_FAILED errno=%d\n",*__error());fflush(0);kill(pid,9);return 1;}
  sleep(1);
 }
 if(!done){
  printf("INFERNO_EXEC_WRAPPER_TIMEOUT child=%d\n",pid);fflush(0);kill(pid,9);
  while(waitpid(pid,&status,0)<0)if(*__error()!=4)break;
 }
 printf("INFERNO_EXEC_WRAPPER_WAIT case=%s raw=%d timed_out=%d expected=%d\n",label,status,!done,noargs?16384:0);fflush(0);return status!=(noargs?16384:0)||!done?1:0;
}

int main(int argc,char **argv){
 if(argc==2 && !strcmp(argv[1],"--matrix")){
  int failures=0;
  failures+=attempt("/private/var/inferno/inferno-launcher",0,1,"data-root-noargs");
  failures+=attempt("/private/var/inferno/inferno-launcher",1,1,"data-mobile-noargs");
  failures+=attempt("/usr/bin/inferno-launcher",1,1,"system-mobile-noargs");
  printf("INFERNO_EXEC_MATRIX_COMPLETE failures=%d\n",failures);fflush(0);return failures?1:0;
 }
 if(argc==2 && !strcmp(argv[1],"--system"))return attempt("/usr/bin/inferno-launcher",1,0,"system-mobile-register");
 return attempt("/private/var/inferno/inferno-launcher",1,0,"data-mobile-register");
}
