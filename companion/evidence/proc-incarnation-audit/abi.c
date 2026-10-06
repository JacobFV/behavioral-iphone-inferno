/* Self-authored narrow ABI verification; no SDK implementation. */
typedef unsigned char u8; typedef unsigned long long u64; typedef unsigned int u32; typedef int i32;
struct owned_unique_info {u8 uuid[16];u64 uniqueid,parent_uniqueid;i32 idversion;u32 reserved2;u64 reserved3,reserved4;};
#define OFF(f) __builtin_offsetof(struct owned_unique_info,f)
_Static_assert(sizeof(struct owned_unique_info)==56,"size");
_Static_assert(OFF(uuid)==0 && OFF(uniqueid)==16 && OFF(parent_uniqueid)==24,"identity offsets");
_Static_assert(OFF(idversion)==32 && OFF(reserved2)==36 && OFF(reserved3)==40 && OFF(reserved4)==48,"tail offsets");
