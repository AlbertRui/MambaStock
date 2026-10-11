# 合并远程4份并行日志 -> 校验完整块数=100 -> 拉回本地
import os, paramiko

c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('i-1.gpushare.com', port=29582, username='root',
          password=os.environ['HY_PW'], timeout=20)

def run(cmd, t=60):
    _, o, e = c.exec_command(cmd, timeout=t)
    return o.read().decode() + e.read().decode()

print(run('cd /hy-tmp/MambaStock/results && '
          'cat log_v3_b.txt log_v3_c.txt log_v3_d.txt >> experiment_log_v3_tuning.txt && '
          "echo 完整块数: $(grep -c '^  DA' experiment_log_v3_tuning.txt) && "
          "echo ALLDONE数: $(grep -c 'ALL DONE' experiment_log_v3_tuning.txt)"))

sftp = c.open_sftp()
sftp.get('/hy-tmp/MambaStock/results/experiment_log_v3_tuning.txt',
         'results/experiment_log_v3_tuning.txt')
sftp.close()
c.close()
print('已拉回本地 results/experiment_log_v3_tuning.txt')
