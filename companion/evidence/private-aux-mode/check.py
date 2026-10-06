import ast, hashlib, json, pathlib, socket, subprocess, sys, time
repo = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2]); out.mkdir()
sys.path.insert(0, str(repo / "companion")); from boot import QMP, digest
source = pathlib.Path("/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/reports/disk-preparation-55/disks/firmware.raw")
before = source.stat(); original_hash = digest(source)
tree = ast.parse((repo / "companion/boot.py").read_text())
node = next(n for n in ast.walk(tree) if isinstance(n, ast.If) and ast.unparse(n.test) == "name in auxiliary" and any(isinstance(x, ast.With) for x in n.body))
code = compile(ast.Module(body=node.body, type_ignores=[]), str(repo / "companion/boot.py"), "exec")
disk = out / "firmware.raw"; auxiliary = {"firmware": {"path": str(source), "sha256": original_hash}}
env = {"disk": disk, "auxiliary": auxiliary, "name": "firmware", "subprocess": subprocess, "digest": digest}
exec(code, env)
assert disk.stat().st_mode & 0o777 == 0o600 and digest(disk) == original_hash
try: exec(code, env)
except FileExistsError: duplicate_rejected = True
else: raise AssertionError("Existing private file was not rejected")
binary = pathlib.Path("/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/build/qemu-system-aarch64")
endpoint = out / "qmp.sock"
command = [str(binary), "-machine", "none", "-accel", "tcg", "-m", "128M", "-S", "-display", "none", "-monitor", "none", "-serial", "none", "-drive", f"file={disk},format=raw,if=none,id=private", "-qmp", f"unix:{endpoint},server=on,wait=off"]
with (out / "stderr.log").open("wb") as log:
 process = subprocess.Popen(command, stdout=log, stderr=log)
 try:
  for _ in range(100):
   if endpoint.exists(): break
   if process.poll() is not None: raise RuntimeError("QEMU exited")
   time.sleep(.05)
  connection=socket.socket(socket.AF_UNIX); connection.connect(str(endpoint)); qmp=QMP(connection,out)
  greeting=qmp.receive(); caps=qmp.execute("qmp_capabilities"); blocks=qmp.execute("query-block")
  assert blocks["return"][0]["inserted"]["ro"] is False
  quit_result=qmp.execute("quit"); assert quit_result["return"] == {}
  assert process.wait(timeout=10)==0; qmp.close(); connection.close()
 finally:
  if process.poll() is None: process.terminate(); process.wait(timeout=10)
after=source.stat(); assert (before.st_ino,before.st_mode,before.st_ctime_ns,before.st_mtime_ns,before.st_size)==(after.st_ino,after.st_mode,after.st_ctime_ns,after.st_mtime_ns,after.st_size)
assert digest(source)==original_hash
result={"scope":"Actual copied frozen auxiliary opened writable by firmware-free QEMU; no guest execution claim", "source":str(source),"source_sha256":original_hash,"source_identity_unchanged":True,"private_mode":"0600","duplicate_rejected":duplicate_rejected,"command":command,"query_block":blocks,"quit":quit_result,"exit_code":0,"boot_source_sha256":digest(repo / "companion/boot.py"),"binary_sha256":digest(binary)}
(out / "result.json").write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2))
