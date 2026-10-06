"""Firmware-free real subprocess/RFB lifecycle checks; no emulator or guest."""
import importlib.util, json, pathlib, socket, struct, tempfile, threading, time
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('refresh',ROOT/'headless_refresh.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
results=[]
for invalid in (0,301,-1,1.5,True):
    try: mod.HeadlessRefresh('/unused',invalid)
    except ValueError: pass
    else: raise AssertionError(invalid)
results.append({'check':'invalid duration rejection','passed':True})
def run(early, fail_save=False):
    with tempfile.TemporaryDirectory() as tmp:
        p=pathlib.Path(tmp); server=socket.socket(socket.AF_UNIX); endpoint=p/'vnc.sock';server.bind(str(endpoint));server.listen(1)
        seen=[]; errors=[]
        def serve():
            try:
                conn,_=server.accept()
                with conn:
                    def read(n):
                        data=b''
                        while len(data)<n:
                            b=conn.recv(n-len(data))
                            if not b: raise EOFError()
                            data+=b
                        return data
                    conn.sendall(b'RFB 003.008\n');assert read(12)==b'RFB 003.008\n'
                    conn.sendall(b'\x01\x01');assert read(1)==b'\x01';conn.sendall(bytes(4));assert read(1)==b'\x01'
                    conn.sendall(struct.pack('>HH',1,1)+bytes(16)+struct.pack('>I',4)+b'test')
                    assert read(20)[0]==0;assert read(8)[0]==2
                    while True:
                        request=read(10);seen.append(request[0]);assert request[0]==3
                        conn.sendall(b'\x00\x00\x00\x01'+struct.pack('>HHHHi',0,0,1,1,0)+bytes((0,0,255,0)))
            except EOFError: pass
            except Exception as error: errors.append(repr(error))
        thread=threading.Thread(target=serve,daemon=True);thread.start()
        with mod.HeadlessRefresh(p,30 if early else 1) as observer:
            observer.start(endpoint)
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                observer.poll()
                if early and observer.report.get('coverage_active'):
                    if fail_save:
                        def broken_save(): raise OSError('simulated persistence failure')
                        observer.save=broken_save
                    break
                if observer.finished: break
                time.sleep(.05)
            else: raise AssertionError('deadline')
        assert endpoint.exists(), 'cleanup occurred after socket namespace removed'
        thread.join(2);server.close();assert not thread.is_alive();assert not errors,errors
        r=observer.report;assert r['exit_code']==0 and not r.get('forced_kill'),r
        assert r['connection_closed_time']>=r['connection_established_time']
        assert not r['observer_report']['pointer_events'] and not r['observer_report']['home_button_events']
        assert bool(r['observer_report'].get('stop_requested'))==early
        assert r['requested_phase_completed']==(not early)
        assert r['resource_first']['start_ticks']==r['start_ticks']
        return {'check':'cleanup despite report persistence failure' if fail_save else ('graceful early stop' if early else 'finite expiry'),'passed':True,'frame_requests':len(seen),'exit_code':r['exit_code'],'coverage_seconds':r['connection_closed_time']-r['connection_established_time'],'requested_phase_completed':r['requested_phase_completed'],'raw_child_resource_sample':r['resource_first']}
results.extend([run(False),run(True),run(True,True)])
print(json.dumps({'scope':'local fake RFB server and real observer subprocess only; no QEMU or iOS','results':results},indent=2))
