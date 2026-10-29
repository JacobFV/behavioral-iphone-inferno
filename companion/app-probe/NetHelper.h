/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Owned root helper for guest networking over USB CDC-NCM (reverse tethering).
 * The launch wrapper forks this before dropping to mobile. It waits for en0 (the NCM
 * interface, present once the USB companion selects configuration 5), assigns a static
 * address, adds a default route, and publishes configd State keys (link, IPv4, DNS) so
 * IPMonitor makes it the primary service and mDNSResponder gets a resolver.
 * Addresses: guest 192.168.77.2/24, host (companion) 192.168.77.1 = router and DNS.
 * No Apple code; CoreFoundation/SystemConfiguration are reached via dlopen/dlsym.
 */
extern void *dlopen(const char *, int);
extern void *dlsym(void *, const char *);
extern int ioctl(int, unsigned long, ...);
extern unsigned int if_nametoindex(const char *);
extern int usleep(unsigned int);
extern int socket(int, int, int), close(int), getpid(void);
extern long write(int, const void *, unsigned long);
extern int printf(const char *, ...), fflush(void *);
extern int *__error(void);

struct inferno_sin { unsigned char len, family; unsigned short port; unsigned int addr; char zero[8]; };
struct inferno_ifaliasreq { char name[16]; struct inferno_sin addr, broad, mask; };
struct inferno_ifreq { char name[16]; struct inferno_sin addr; };

#define INFERNO_NET_IF "en0"
#define INFERNO_SIOCAIFADDR 0x8040691aUL  /* _IOW('i', 26, struct ifaliasreq) */
#define INFERNO_SIOCGIFADDR 0xc0206921UL  /* _IOWR('i', 33, struct ifreq) */
static unsigned int inferno_ip(unsigned a, unsigned b, unsigned c, unsigned d) { return a | b << 8 | c << 16 | d << 24; }
static struct inferno_sin inferno_sa(unsigned int addr) { struct inferno_sin s = {16, 2, 0, addr, {0}}; return s; }
static void inferno_name(char *dst) { const char *s = INFERNO_NET_IF; int i = 0; for (; s[i]; i++) dst[i] = s[i]; for (; i < 16; i++) dst[i] = 0; }

static int inferno_has_address(int fd) {
  struct inferno_ifreq r; inferno_name(r.name); r.addr = inferno_sa(0);
  return !ioctl(fd, INFERNO_SIOCGIFADDR, &r) && r.addr.addr == inferno_ip(192, 168, 77, 2);
}

static int inferno_add_route(void) {
  struct { unsigned short msglen; unsigned char version, type; unsigned short index, pad; int flags, addrs, pid, seq, err, use;
           unsigned int inits, rmx[14]; struct inferno_sin dst, gw, mask; } m;
  char *p = (char *)&m; for (unsigned long i = 0; i < sizeof m; i++) p[i] = 0;
  m.msglen = sizeof m; m.version = 5; m.type = 1; /* RTM_ADD */
  m.flags = 0x1 | 0x2 | 0x800; /* RTF_UP | RTF_GATEWAY | RTF_STATIC */
  m.addrs = 0x1 | 0x2 | 0x4;   /* RTA_DST | RTA_GATEWAY | RTA_NETMASK */
  m.pid = getpid(); m.seq = 1;
  m.dst = inferno_sa(0); m.gw = inferno_sa(inferno_ip(192, 168, 77, 1)); m.mask = inferno_sa(0);
  int fd = socket(17, 3, 0); /* PF_ROUTE, SOCK_RAW */
  if (fd < 0) return -1;
  long n = write(fd, &m, sizeof m); int e = *__error(); close(fd);
  return n == (long)sizeof m ? 0 : (e == 17 /* EEXIST */ ? 0 : -e);
}

typedef const void *CFT;
static int inferno_publish(void) {
  void *cf = dlopen("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation", 1);
  void *sc = dlopen("/System/Library/Frameworks/SystemConfiguration.framework/SystemConfiguration", 1);
  if (!cf || !sc) return -1;
  CFT (*str)(CFT, const char *, unsigned) = dlsym(cf, "CFStringCreateWithCString");
  CFT (*arr)(CFT, CFT *, long, CFT) = dlsym(cf, "CFArrayCreate");
  CFT (*dict)(CFT, CFT *, CFT *, long, CFT, CFT) = dlsym(cf, "CFDictionaryCreate");
  CFT acb = dlsym(cf, "kCFTypeArrayCallBacks"), kcb = dlsym(cf, "kCFTypeDictionaryKeyCallBacks"),
      vcb = dlsym(cf, "kCFTypeDictionaryValueCallBacks");
  CFT *yes = dlsym(cf, "kCFBooleanTrue");
  CFT (*create)(CFT, CFT, CFT, CFT) = dlsym(sc, "SCDynamicStoreCreate");
  unsigned char (*set)(CFT, CFT, CFT) = dlsym(sc, "SCDynamicStoreSetValue");
  int (*scerror)(void) = dlsym(sc, "SCError");
  if (!str || !arr || !dict || !acb || !kcb || !vcb || !yes || !create || !set || !scerror) return -2;
#define S(x) str(0, x, 0x08000100)
  CFT store = create(0, S("org.inferno.net"), 0, 0);
  if (!store) return -3;
  CFT one_addr[] = {S("192.168.77.2")}, one_mask[] = {S("255.255.255.0")}, one_dns[] = {S("192.168.77.1")};
  CFT link_k[] = {S("Active")}, link_v[] = {*yes};
  CFT ip_k[] = {S("Addresses"), S("SubnetMasks"), S("Router"), S("InterfaceName")};
  CFT ip_v[] = {arr(0, one_addr, 1, acb), arr(0, one_mask, 1, acb), S("192.168.77.1"), S(INFERNO_NET_IF)};
  CFT dns_k[] = {S("ServerAddresses")}, dns_v[] = {arr(0, one_dns, 1, acb)};
  int failures = 0;
  if (!set(store, S("State:/Network/Interface/" INFERNO_NET_IF "/Link"), dict(0, link_k, link_v, 1, kcb, vcb))) failures++;
  if (!set(store, S("State:/Network/Service/org.inferno.ncm/IPv4"), dict(0, ip_k, ip_v, 4, kcb, vcb))) failures++;
  if (!set(store, S("State:/Network/Service/org.inferno.ncm/DNS"), dict(0, dns_k, dns_v, 1, kcb, vcb))) failures++;
#undef S
  return failures ? -100 - scerror() : 0;
}

/* Runs forever in a forked root child: (re)configures whenever en0 exists without our address. */
static void inferno_net_loop(void) {
  int seen = 0;
  for (;;) {
    if (if_nametoindex(INFERNO_NET_IF)) {
      int fd = socket(2, 2, 0); /* AF_INET, SOCK_DGRAM */
      if (fd >= 0 && !inferno_has_address(fd)) {
        struct inferno_ifaliasreq r; inferno_name(r.name);
        r.addr = inferno_sa(inferno_ip(192, 168, 77, 2)); r.broad = inferno_sa(inferno_ip(192, 168, 77, 255));
        r.mask = inferno_sa(inferno_ip(255, 255, 255, 0));
        int a = ioctl(fd, INFERNO_SIOCAIFADDR, &r), ae = a ? *__error() : 0;
        int rt = inferno_add_route(), pub = inferno_publish();
        printf("INFERNO_NET_CONFIGURED if=%s addr=%d errno=%d route=%d publish=%d\n", INFERNO_NET_IF, a, ae, rt, pub); fflush(0);
        seen = 1;
      }
      if (fd >= 0) close(fd);
    } else if (seen) { printf("INFERNO_NET_INTERFACE_GONE if=%s\n", INFERNO_NET_IF); fflush(0); seen = 0; }
    usleep(3000000);
  }
}
