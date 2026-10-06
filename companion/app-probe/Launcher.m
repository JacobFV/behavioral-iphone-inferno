// SPDX-License-Identifier: AGPL-3.0-or-later
// Requests registration and launch through original guest CoreServices only.
#import "LaunchServicesNarrow.h"
#include "EventRecord.h"
#include "OwnedClock.h"

static const char *utf8(NSString *text) {
    const char *value = [text UTF8String];
    return value ? value : "(nil)";
}
static void emit(const char *text) {
    unsigned long length = 0;
    while (text[length]) ++length;
    (void)write(2, text, length);
    NSLog(@"%s", text);
}
static void status(const char *event, int attempt, int result) {
    char text[256];
    snprintf(text, sizeof(text), "INFERNO_LAUNCHER_V1 event=%s attempt=%d result=%d\n",
             event, attempt, result);
    emit(text);
}
#if INFERNO_OPEN_DIAGNOSTIC
// Original synchronous XPC method; its BOOL wrapper reads the callback result
// immediately after the call, without a run-loop wait.
static BOOL openCallbackFinished, openCallbackAccepted;
static int openCallbackAttempt;
static unsigned long long openRequestTicks,openCallbackTicks;
extern int getpid(void);
#endif
#if INFERNO_OPEN_DIAGNOSTIC
static char controlledRequest[33];
extern int getuid(void);
static int controlled_open(const char *request) {
    for(unsigned i=0;i<32;i++) {char c=request[i];if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return 64;controlledRequest[i]=c;}
    if(request[32] || getuid()!=501)return 64;
    controlledRequest[32]=0;alarm(120);
    @autoreleasepool {
        Class cls=NSClassFromString(@"LSApplicationWorkspace");
        if(!cls) {status("open-only-missing-class",0,1);return 69;}
        LSApplicationWorkspace *workspace=[cls defaultWorkspace];
        openCallbackFinished=0;openCallbackAccepted=0;openCallbackTicks=0;
        openRequestTicks=mach_absolute_time();
        [workspace openApplicationWithBundleIdentifier:@"org.inferno.companion.probe" configuration:nil completionHandler:^(BOOL accepted,id errorObject) {
            openCallbackTicks=mach_absolute_time();
            openCallbackAccepted=accepted;openCallbackFinished=1;
            NSError *error=errorObject;char text[1024];
            snprintf(text,sizeof(text),"INFERNO_OPEN_CALLBACK request_id=%s accepted=%d domain=%.160s code=%ld description=%.640s\n",controlledRequest,accepted,utf8([error domain]),[error code],utf8([error localizedDescription]));emit(text);
        }];
        char boot[37];struct inferno_timebase base={0,0};
        int br=inferno_boot_uuid(boot),tr=mach_timebase_info(&base);
        if(!openCallbackFinished || br || tr || !base.numer || !base.denom || !openRequestTicks || openCallbackTicks<openRequestTicks) {
            status("open-only-incomplete-timing",0,1);return 70;
        }
        char text[384];snprintf(text,sizeof(text),"INFERNO_OPEN_TIMING_V1 request_id=%s boot=%s pid=%d request_ticks=%llu callback_ticks=%llu numer=%u denom=%u accepted=%d\n",controlledRequest,boot,getpid(),openRequestTicks,openCallbackTicks,base.numer,base.denom,openCallbackAccepted);emit(text);
        alarm(0);return openCallbackAccepted?0:1;
    }
}
#endif
int main(int argc, char **argv) {
#if INFERNO_OPEN_DIAGNOSTIC
    if(argc==3 && !strcmp(argv[1],"--open-only"))return controlled_open(argv[2]);
#endif
    if (argc != 3) {
        emit("usage: inferno-launcher /absolute/InfernoProbe.app org.inferno.companion.probe\n");
        return 64;
    }
    // SIGALRM's default termination bounds even a blocked framework IPC call.
    alarm(120);
    status("start-watchdog-120s", 0, 0);
    for (int attempt = 1; attempt <= 30; ++attempt) {
        @autoreleasepool {
            NSString *path = [NSString stringWithUTF8String:argv[1]];
            NSString *identifier = [NSString stringWithUTF8String:argv[2]];
#if !INFERNO_REGISTER_DICTIONARY
            NSURL *url = [NSURL fileURLWithPath:path];
#endif
            Class workspaceClass = NSClassFromString(@"LSApplicationWorkspace");
            Class proxyClass = NSClassFromString(@"LSApplicationProxy");
            if (!workspaceClass || !proxyClass) {
                status("missing-class", attempt, 1);
            } else {
                LSApplicationWorkspace *workspace = [workspaceClass defaultWorkspace];
#if INFERNO_REGISTER_DICTIONARY
                // Exact owned Info.plist fields, plus the actual installed path.
                // Original ABI/control flow is recorded in registration-path-inspection.json.
                Class dictionaryClass = NSClassFromString(@"NSMutableDictionary");
                NSMutableDictionary *record = [dictionaryClass dictionaryWithContentsOfFile:
                    [path stringByAppendingPathComponent:@"Info.plist"]];
                if (!record || ![[record objectForKey:@"CFBundleIdentifier"] isEqualToString:identifier]) {
                    status("dictionary-input-invalid", attempt, 1);
                    return 65;
                }
                [record setObject:path forKey:@"Path"];
                // Match original installd classification for this owned bundle
                // directly on System. Do not assert signer/profile/trust fields.
                // See evidence/owned-system-app-classification-inspection.json.
                if ([path isEqualToString:@"/Applications/InfernoProbe.app"] &&
                    [identifier isEqualToString:@"org.inferno.companion.probe"])
                    [record setObject:@"System" forKey:@"ApplicationType"];
                BOOL registration = [workspace registerApplicationDictionary:record];
                status("register-dictionary-boolean", attempt, registration);
#else
                BOOL registration = [workspace registerApplication:url];
                status("register-boolean", attempt, registration);
#endif
                LSApplicationProxy *proxy = [proxyClass applicationProxyForIdentifier:identifier];
                id appState = [proxy respondsToSelector:@selector(appState)] ? [proxy appState] : nil;
                BOOL valid = [appState respondsToSelector:@selector(isValid)] && [appState isValid];
                char detail[2048];
                snprintf(detail, sizeof(detail),
                         "INFERNO_LAUNCHER_V1 event=proxy attempt=%d valid=%d bundle=%s container=%s type=%s\n",
                         attempt, valid, utf8([[proxy bundleURL] path]),
                         utf8([[proxy containerURL] path]), utf8([proxy applicationType]));
                emit(detail);
                if (registration && valid) {
#if INFERNO_OPEN_DIAGNOSTIC
                    openCallbackFinished = 0;
                    openCallbackAccepted = 0;
                    openCallbackAttempt = attempt;
                    openCallbackTicks=0;
                    openRequestTicks=mach_absolute_time();
                    [workspace openApplicationWithBundleIdentifier:identifier configuration:nil
                        completionHandler:^(BOOL accepted, id errorObject) {
                            openCallbackTicks=mach_absolute_time();
                            NSError *error = errorObject;
                            char message[1536];
                            snprintf(message, sizeof(message),
                                "INFERNO_LAUNCHER_V1 event=open-callback attempt=%d accepted=%d domain=%.160s code=%ld description=%.1024s\n",
                                openCallbackAttempt, accepted, utf8([error domain]),
                                [error code], utf8([error localizedDescription]));
                            emit(message);
                            if (error) {
                                // Original FBS stores the specific denial in these
                                // fields; inspect only one underlying NSError.
                                id underlyingObject = [[error userInfo] objectForKey:@"NSUnderlyingError"];
                                NSError *underlying =
                                    [underlyingObject respondsToSelector:@selector(domain)] &&
                                    [underlyingObject respondsToSelector:@selector(code)] &&
                                    [underlyingObject respondsToSelector:@selector(localizedDescription)]
                                    ? underlyingObject : nil;
                                snprintf(message, sizeof(message),
                                    "INFERNO_LAUNCHER_V1 event=open-error-detail attempt=%d failure_reason=%.512s underlying_present=%d underlying_domain=%.160s underlying_code=%ld underlying_description=%.512s\n",
                                    openCallbackAttempt, utf8([error localizedFailureReason]),
                                    underlying != nil, utf8([underlying domain]),
                                    [underlying code], utf8([underlying localizedDescription]));
                                emit(message);
                            }
                            openCallbackAccepted = accepted;
                            openCallbackFinished = 1;
                        }];
                    if (!openCallbackFinished) {
                        // Do not block an unknown callback queue if behavior differs.
                        status("open-callback-not-delivered", attempt, 1);
                        return 70;
                    }
                    char boot[37];struct inferno_timebase base={0,0};
                    int bootResult=inferno_boot_uuid(boot);
                    int timeResult=mach_timebase_info(&base);
                    if(!bootResult && !timeResult && base.numer && base.denom && openRequestTicks && openCallbackTicks>=openRequestTicks) {
                        char timing[320];
                        snprintf(timing,sizeof(timing),"INFERNO_LAUNCH_TIMING_V1 boot=%s pid=%d attempt=%d request_ticks=%llu callback_ticks=%llu numer=%u denom=%u accepted=%d\n",boot,getpid(),attempt,openRequestTicks,openCallbackTicks,base.numer,base.denom,openCallbackAccepted);
                        emit(timing);
                    } else {
                        char timing[192];snprintf(timing,sizeof(timing),"INFERNO_LAUNCH_TIMING_ERROR boot_result=%d time_result=%d valid_order=%d\n",bootResult,timeResult,openRequestTicks && openCallbackTicks>=openRequestTicks);emit(timing);
                    }
                    BOOL opened = openCallbackAccepted;
#else
                    BOOL opened = [workspace openApplicationWithBundleID:identifier];
#endif
                    status("open-request", attempt, opened);
                    if (opened) {
                        // This is only a service acknowledgement, not screenshot evidence.
                        status("request-accepted-not-visual-proof", attempt, 0);
                        alarm(0);
                        return 0;
                    }
                }
            }
        }
        if (attempt < 30) sleep(3);
    }
    status("attempts-exhausted", 30, 1);
    alarm(0);
    return 1;
}
