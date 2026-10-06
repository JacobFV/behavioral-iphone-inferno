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
int inferno_app_event_path(char *output,unsigned long capacity) {
    @autoreleasepool {
        Class cls=NSClassFromString(@"LSApplicationProxy");
        if(!cls)return 1;
        InfernoLSProxy *proxy=[cls applicationProxyForIdentifier:@"org.inferno.companion.probe"];
        if(![[[proxy bundleURL] path] isEqualToString:@"/Applications/InfernoProbe.app"])return 2;
        NSString *container=[[proxy dataContainerURL] path];
        if(!container)return 3;
        if([container isEqualToString:@"/var/mobile"] || [container isEqualToString:@"/var/mobile/"] || [container isEqualToString:@"/private/var/mobile"] || [container isEqualToString:@"/private/var/mobile/"])return 4;
        NSString *path=[[container stringByAppendingPathComponent:@"Library/Caches"] stringByAppendingPathComponent:@"org.inferno.companion.probe.events"];
        const char *value=[path UTF8String];
        int n=value?snprintf(output,capacity,"%s",value):-1;
        return n>0 && (unsigned long)n<capacity && output[0]=='/'?0:5;
    }
}
