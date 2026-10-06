// SPDX-License-Identifier: AGPL-3.0-or-later
// Narrow Darwin socket ABI for an owned guest-loopback event channel.
#ifndef INFERNO_LOOPBACK_EVENT_H
#define INFERNO_LOOPBACK_EVENT_H
struct inferno_loopback_address {unsigned char length,family,port[2],address[4],padding[8];};
struct inferno_pollfd {int fd;short events,revents;};
_Static_assert(sizeof(struct inferno_loopback_address)==16,"Darwin sockaddr_in");
_Static_assert(sizeof(struct inferno_pollfd)==8,"Darwin pollfd");
extern int socket(int,int,int),connect(int,const void *,unsigned),bind(int,const void *,unsigned),listen(int,int),accept(int,void *,unsigned *);
extern int fcntl(int,int,...),poll(struct inferno_pollfd *,unsigned,int),close(int),*__error(void);
extern int setsockopt(int,int,int,const void *,unsigned),getsockopt(int,int,int,void *,unsigned *);
extern long send(int,const void *,unsigned long,int),recv(int,void *,unsigned long,int);
static inline struct inferno_loopback_address inferno_loopback_address(void) {
    struct inferno_loopback_address a={16,2,{37373>>8,37373&255},{127,0,0,1},{0}};return a;
}
static inline int inferno_nonblocking(int fd) {
    int flags=fcntl(fd,3,0);return flags<0?-1:fcntl(fd,4,flags|4);
}
static inline int inferno_send_event(const char *line,unsigned length,int *error) {
    int fd=socket(2,1,0);*error=0;if(fd<0) {*error=*__error();return -1;}
    int one=1,result=-2;
    if(inferno_nonblocking(fd) || setsockopt(fd,0xffff,0x1022,&one,sizeof(one))) {*error=*__error();goto done;}
    result=-3;
    struct inferno_loopback_address a=inferno_loopback_address();
    if(connect(fd,&a,sizeof(a))) {
        *error=*__error();if(*error!=36 && *error!=35)goto done;
        int connected=0;
        for(unsigned attempt=0;attempt<8;attempt++) {
            struct inferno_pollfd p={fd,4,0};int n=poll(&p,1,250);
            if(n<0) {if(*__error()==4)continue;*error=*__error();goto done;}
            if(!n)continue;
            unsigned size=sizeof(*error);
            if(getsockopt(fd,0xffff,0x1007,error,&size)) {*error=*__error();goto done;}
            if(size!=sizeof(*error)) {*error=22;goto done;}
            if(*error)goto done;
            if(p.revents&4) {connected=1;break;}
        }
        if(!connected) {*error=60;goto done;}
    }
    result=-4;
    unsigned sent=0;
    for(unsigned attempt=0;attempt<8 && sent<length;attempt++) {
        long n=send(fd,line+sent,length-sent,0);
        if(n>0) {sent+=(unsigned)n;continue;}
        if(!n) {*error=32;goto done;}
        *error=*__error();if(*error!=35 && *error!=4)goto done;
        struct inferno_pollfd p={fd,4,0};(void)poll(&p,1,250);
    }
    if(sent!=length) {*error=60;goto done;}
    *error=0;result=0;
done:
    close(fd);return result;
}
#endif
