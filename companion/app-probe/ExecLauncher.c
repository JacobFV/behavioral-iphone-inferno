/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Owned diagnostic: original guest execve after dropping to mobile credentials.
 * No launch privileges, registration workaround or file writes.
 */
extern int printf(const char *,...),fflush(void *),fork(void),waitpid(int,int*,int);
extern int setgroups(int,const unsigned int *),setgid(unsigned int),setuid(unsigned int);
extern unsigned int getuid(void),getgid(void),sleep(unsigned int);
extern int kill(int,int);
extern int execve(const char *,char *const[],char *const[]),*__error(void);
extern void _exit(int);
int main(void){
 printf("INFERNO_EXEC_WRAPPER_BEGIN watchdog=150 uid=%u gid=%u\n",getuid(),getgid());fflush(0);
 int pid=fork();
 if(!pid){
  if(setgroups(0,0)||setgid(501)||setuid(501)){
   printf("INFERNO_EXEC_WRAPPER_CREDENTIALS_FAILED errno=%d\n",*__error());fflush(0);_exit(126);
  }
  printf("INFERNO_EXEC_WRAPPER_CHILD uid=%u gid=%u\n",getuid(),getgid());fflush(0);
  char *argv[]={"/private/var/inferno/inferno-launcher","/private/var/inferno/InfernoProbe.app","org.inferno.companion.probe",0};
  char *env[]={"PATH=/usr/bin:/bin:/usr/sbin:/sbin","HOME=/var/mobile","CFFIXED_USER_HOME=/var/mobile","TMPDIR=/var/tmp",0};
  execve(argv[0],argv,env);
  printf("INFERNO_EXEC_WRAPPER_EXEC_FAILED errno=%d uid=%u gid=%u\n",*__error(),getuid(),getgid());fflush(0);_exit(127);
 }
 if(pid<0){printf("INFERNO_EXEC_WRAPPER_FORK_FAILED errno=%d\n",*__error());fflush(0);return 1;}
 int status=-1,done=0;
 for(int seconds=0;seconds<150;seconds++){
  int result=waitpid(pid,&status,1); /* Darwin WNOHANG */
  if(result==pid){done=1;break;}
  if(result<0 && *__error()!=4){printf("INFERNO_EXEC_WRAPPER_WAIT_FAILED errno=%d\n",*__error());fflush(0);kill(pid,9);return 1;}
  sleep(1);
 }
 if(!done){
  printf("INFERNO_EXEC_WRAPPER_TIMEOUT child=%d\n",pid);fflush(0);kill(pid,9);
  while(waitpid(pid,&status,0)<0)if(*__error()!=4)break;
 }
 printf("INFERNO_EXEC_WRAPPER_WAIT raw=%d timed_out=%d\n",status,!done);fflush(0);return status||!done?1:0;
}
