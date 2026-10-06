/* SPDX-License-Identifier: AGPL-3.0-or-later */
void inferno_open_start(int);
int inferno_open_handle(const char *); /* 0 other protocol, 1 accepted, -1 rejected */
void inferno_open_poll(void);
int inferno_open_busy(void);
void inferno_open_close(void);
int inferno_command_id_seen(const char *);
void inferno_command_id_remember(const char *);
