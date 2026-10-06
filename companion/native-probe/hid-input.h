/* Owned bounded automation protocol; no original implementation code. */
struct inferno_gesture {
    char request_id[33];
    int swipe;
    unsigned x0,y0,x1,y1,duration_ms;
};
int inferno_hid_stopping(void);
/* Backend must return only an attempt status; never assert OS/UI delivery. */
int inferno_hid_dispatch(const struct inferno_gesture *);
