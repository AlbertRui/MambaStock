# 并行调参启动器：清理远程残留进程 -> 上传并行脚本 -> 4 路 worker 同卡并行
import os, paramiko, time

c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('i-1.gpushare.com', port=29582, username='root',
          password=os.environ['HY_PW'], timeout=20)

def run(cmd, t=30):
    _, o, e = c.exec_command(cmd, timeout=t)
    out = o.read().decode(); err = e.read().decode()
    return out + err

# 1) 杀掉顺序任务的远程残留（本地驱动已停，远程可能还在跑）
print(run("pkill -f run_tuning_v3.sh; pkill -f 'train.py --csv'; pkill -f train_panel.py; sleep 2; "
          "ps aux | grep -E 'train|run_tuning' | grep -v grep | wc -l"))

# 2) 主日志现状（完整块数）
print(run("grep -c '^  DA' /hy-tmp/MambaStock/results/experiment_log_v3_tuning.txt"))

# 3) 上传并行脚本
sftp = c.open_sftp()
sftp.put('run_tuning_v3_par.sh', '/hy-tmp/MambaStock/run_tuning_v3_par.sh')
sftp.close()
run('dos2unix -q /hy-tmp/MambaStock/run_tuning_v3_par.sh')

# 4) 启动 4 路 worker：a 续写主日志(跳过已完成6组)，b/c/d 独立日志
base = 'cd /hy-tmp/MambaStock && export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 PY=python3'
cmd = ' && '.join([
    base,
    'nohup bash run_tuning_v3_par.sh a > results/par_a.out 2>&1 &',
    'LOG=results/log_v3_b.txt nohup bash run_tuning_v3_par.sh b > results/par_b.out 2>&1 &',
    'LOG=results/log_v3_c.txt nohup bash run_tuning_v3_par.sh c > results/par_c.out 2>&1 &',
    'LOG=results/log_v3_d.txt nohup bash run_tuning_v3_par.sh d > results/par_d.out 2>&1 &',
    'sleep 8; ps aux | grep run_tuning_v3_par | grep -v grep | wc -l',
])
print(run(cmd, t=40))

# 5) 确认 GPU 上 4 个训练进程已起来
time.sleep(20)
print(run('nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader | wc -l'))
print(run('tail -n 3 /hy-tmp/MambaStock/results/experiment_log_v3_tuning.txt'))
c.close()
