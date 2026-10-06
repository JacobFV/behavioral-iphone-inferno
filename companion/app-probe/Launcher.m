// SPDX-License-Identifier: AGPL-3.0-or-later
// Requests registration and launch through original guest CoreServices only.
#import "LaunchServicesNarrow.h"

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
#endif
int main(int argc, char **argv) {
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
                    [workspace openApplicationWithBundleIdentifier:identifier configuration:nil
                        completionHandler:^(BOOL accepted, id errorObject) {
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
