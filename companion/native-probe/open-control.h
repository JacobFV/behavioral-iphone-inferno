/* SPDX-License-Identifier: AGPL-3.0-or-later */
void inferno_open_start(int);
int inferno_open_handle(const char *); /* 0 other protocol, 1 accepted, -1 rejected */
void inferno_open_poll(void);
int inferno_open_busy(void);
void inferno_open_close(void);
/* Bounds shared with the host transport in qmp_control.py; keep them equal. */
#define INFERNO_HID_MAX_REQUESTS 2048
#define INFERNO_HID_LIFETIME_SECONDS 21600
#define INFERNO_COMMAND_IDS (INFERNO_HID_MAX_REQUESTS + 52)
int inferno_command_id_seen(const char *);
void inferno_command_id_remember(const char *);
