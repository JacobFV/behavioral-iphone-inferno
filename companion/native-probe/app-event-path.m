// SPDX-License-Identifier: AGPL-3.0-or-later
// Query only the owned application's original LaunchServices record.
#import "../app-probe/UIKitNarrow.h"
#include "../app-probe/EventRecord.h"
extern Class NSClassFromString(NSString *);
@interface InfernoLSProxy : NSObject
+ (instancetype)applicationProxyForIdentifier:(NSString *)identifier;
- (NSURL *)bundleURL;
- (NSURL *)dataContainerURL;
@end
@interface MCMAppDataContainer : NSObject
+ (instancetype)containerWithIdentifier:(NSString *)identifier createIfNecessary:(BOOL)create existed:(BOOL *)existed error:(NSError **)error;
- (NSURL *)url;
@end
extern int printf(const char *,...),fflush(void *);
int inferno_app_event_path(char *output,unsigned long capacity) {
    @autoreleasepool {
        Class cls=NSClassFromString(@"LSApplicationProxy");
        if(!cls)return 1;
        InfernoLSProxy *proxy=[cls applicationProxyForIdentifier:@"org.inferno.companion.probe"];
        if(![[[proxy bundleURL] path] isEqualToString:@"/Applications/InfernoProbe.app"])return 2;
        NSString *container=[[proxy dataContainerURL] path];
        if(!container) {
            BOOL existed=0;NSError *error=nil;
            MCMAppDataContainer *existing=[MCMAppDataContainer containerWithIdentifier:@"org.inferno.companion.probe" createIfNecessary:0 existed:&existed error:&error];
            static unsigned reports;
            if(reports++<8) {printf("INFERNO_EVENT_MCM_LOOKUP create=0 object=%d existed=%d error_code=%ld\n",existing!=nil,existed,error?[error code]:0);fflush(0);}
            container=[[existing url] path];
            if(!container)return 3;
        }
        if([container isEqualToString:@"/var/mobile"] || [container isEqualToString:@"/var/mobile/"] || [container isEqualToString:@"/private/var/mobile"] || [container isEqualToString:@"/private/var/mobile/"])return 4;
        NSString *path=[[container stringByAppendingPathComponent:@"Library/Caches"] stringByAppendingPathComponent:@"org.inferno.companion.probe.events"];
        const char *value=[path UTF8String];
        int n=value?snprintf(output,capacity,"%s",value):-1;
        return n>0 && (unsigned long)n<capacity && output[0]=='/'?0:5;
    }
}
