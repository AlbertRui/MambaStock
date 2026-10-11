# 查看远程进程实况并精确清理，然后正确启动 4 路并行 worker
import os, paramiko, time

c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('i-1.gpushare.com', port=29582, username='root',
          password=os.environ['HY_PW'], timeout=20)

def run(cmd, t=60):
    _, o, e = c.exec_command(cmd, timeout=t)
    return o.read().decode() + e.read().decode()

print('--- 进程实况 ---')
print(run("ps aux | grep -E 'train|run_tuning' | grep -v grep | awk '{print $2, $11, $12, $13}'"))
print('--- 杀掉 ---')
print(run("pkill -9 -f run_tuning_v3 ; pkill -9 -f 'train.py' ; pkill -9 -f train_panel ; sleep 3 ; ps aux | grep -E 'train|run_tuning' | grep -v grep | wc -l"))
print('--- GPU 占用 ---')
print(run('nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader'))
c.close()
