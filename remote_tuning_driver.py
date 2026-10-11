# 远程驱动：上传调参脚本并在4090上执行，流式回传进度
import os, paramiko, time

c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('i-1.gpushare.com', port=29582, username='root',
          password=os.environ['HY_PW'], timeout=20)
sftp = c.open_sftp()
sftp.put('run_tuning_v3.sh', '/hy-tmp/MambaStock/run_tuning_v3.sh')
sftp.close()
_, out, _ = c.exec_command('cd /hy-tmp/MambaStock && dos2unix -q run_tuning_v3.sh 2>/dev/null; PY=python3 bash run_tuning_v3.sh 2>&1', timeout=None)
t0 = time.time()
done = 0
while not out.channel.exit_status_ready():
    line = out.readline()
    if line:
        if line.startswith('==='):
            done += 1
            print(f'[{time.time()-t0:6.0f}s] ({done}/100)', line, end='', flush=True)
        elif '早停于' in line or '跳过' in line or 'ALL DONE' in line:
            print(f'[{time.time()-t0:6.0f}s]', line, end='', flush=True)
    else:
        time.sleep(3)
print(out.read().decode())
print('exit:', out.channel.recv_exit_status())
c.close()
