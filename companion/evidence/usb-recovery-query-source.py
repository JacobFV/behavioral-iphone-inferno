import ctypes as C, ctypes.util, json
lib=C.CDLL(ctypes.util.find_library('imobiledevice-1.0'))
lib.idevice_new.argtypes=[C.POINTER(C.c_void_p),C.c_char_p]
lib.restored_client_new.argtypes=[C.c_void_p,C.POINTER(C.c_void_p),C.c_char_p]
lib.restored_query_type.argtypes=[C.c_void_p,C.POINTER(C.c_char_p),C.POINTER(C.c_uint64)]
lib.restored_client_free.argtypes=[C.c_void_p]
lib.idevice_free.argtypes=[C.c_void_p]
device=C.c_void_p(); client=C.c_void_p(); kind=C.c_char_p(); version=C.c_uint64()
r=lib.idevice_new(C.byref(device),b'00008030-1122334455667788');print(json.dumps({'idevice_new':r}),flush=True)
if r:raise SystemExit(1)
try:
 r=lib.restored_client_new(device,C.byref(client),b'inferno-readonly-query');print(json.dumps({'restored_client_new':r}),flush=True)
 if r:raise SystemExit(1)
 try:
  r=lib.restored_query_type(client,C.byref(kind),C.byref(version));print(json.dumps({'restored_query_type':r,'type':kind.value.decode() if kind.value else None,'version':version.value}),flush=True)
 finally:lib.restored_client_free(client)
finally:lib.idevice_free(device)
