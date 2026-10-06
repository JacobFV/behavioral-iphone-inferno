// SPDX-License-Identifier: AGPL-3.0-or-later
// Self-authored ABI declarations for one owned diagnostic launcher, not an SDK.
typedef signed char BOOL;
#ifndef nil
#define nil ((id)0)
#endif
@class NSString, NSURL;
__attribute__((objc_root_class))
@interface NSObject
- (BOOL)respondsToSelector:(SEL)selector;
- (NSString *)description;
@end
@interface NSString : NSObject
+ (instancetype)stringWithUTF8String:(const char *)text;
- (const char *)UTF8String;
@end
@interface NSURL : NSObject
+ (instancetype)fileURLWithPath:(NSString *)path;
- (NSString *)path;
@end
@interface LSApplicationWorkspace : NSObject
+ (instancetype)defaultWorkspace;
- (BOOL)openApplicationWithBundleID:(NSString *)identifier;
@end
@interface LSApplicationProxy : NSObject
+ (instancetype)applicationProxyForIdentifier:(NSString *)identifier;
- (NSURL *)bundleURL;
- (NSURL *)containerURL;
- (NSString *)applicationType;
- (id)appState;
@end
@interface NSObject (ProbeApplicationState)
- (BOOL)isValid;
@end
extern Class NSClassFromString(NSString *name);
extern int LSRegisterURL(const void *url, unsigned char update);
extern void NSLog(NSString *format, ...);
extern int snprintf(char *buffer, unsigned long size, const char *format, ...);
extern long write(int descriptor, const void *buffer, unsigned long length);
extern unsigned int sleep(unsigned int seconds);
extern unsigned int alarm(unsigned int seconds);
