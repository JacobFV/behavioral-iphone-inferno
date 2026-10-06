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
            NSURL *url = [NSURL fileURLWithPath:path];
            int registration = LSRegisterURL((const void *)url, 0);
            status("register-osstatus", attempt, registration);
            Class workspaceClass = NSClassFromString(@"LSApplicationWorkspace");
            Class proxyClass = NSClassFromString(@"LSApplicationProxy");
            if (!workspaceClass || !proxyClass) {
                status("missing-class", attempt, 1);
            } else {
                LSApplicationProxy *proxy = [proxyClass applicationProxyForIdentifier:identifier];
                id appState = [proxy respondsToSelector:@selector(appState)] ? [proxy appState] : nil;
                BOOL valid = [appState respondsToSelector:@selector(isValid)] && [appState isValid];
                char detail[2048];
                snprintf(detail, sizeof(detail),
                         "INFERNO_LAUNCHER_V1 event=proxy attempt=%d valid=%d bundle=%s container=%s type=%s\n",
                         attempt, valid, utf8([[proxy bundleURL] path]),
                         utf8([[proxy containerURL] path]), utf8([proxy applicationType]));
                emit(detail);
                if (registration == 0 && valid) {
                    LSApplicationWorkspace *workspace = [workspaceClass defaultWorkspace];
                    BOOL opened = [workspace openApplicationWithBundleID:identifier];
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
