# 精确清理远程残留（用括号正则避免 pkill 误杀自身 shell），确认后启动 4 路并行 worker
import os, paramiko, time

c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('i-1.gpushare.com', port=29582, username='root',
          password=os.environ['HY_PW'], timeout=20)

def run(cmd, t=60):
    _, o, e = c.exec_command(cmd, timeout=t)
    return o.read().decode() + e.read().decode()

print('--- 清理前 ---')
print(run("pgrep -af 'train[.]py|train_panel[.]py|run_tuning[_]v3'"))
print(run("pkill -9 -f 'run_tuning[_]v3'; pkill -9 -f 'train[.]py'; pkill -9 -f 'train_panel[.]py'; sleep 3"))
print('--- 清理后（应为空）---')
print(run("pgrep -af 'train[.]py|train_panel[.]py|run_tuning[_]v3'"))
print('--- GPU（应为空）---')
print(run('nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader'))

# 启动 4 路 worker（setsid 脱离会话，nohup 双保险；每路限 2 线程避免 CPU 争抢）
print('--- 启动 ---')
cmd = (
    'cd /hy-tmp/MambaStock && '
    'export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 PY=python3; '
    'LOG=results/experiment_log_v3_tuning.txt setsid nohup bash run_tuning_v3_par.sh a > results/par_a.out 2>&1 < /dev/null & '
    'LOG=results/log_v3_b.txt setsid nohup bash run_tuning_v3_par.sh b > results/par_b.out 2>&1 < /dev/null & '
    'LOG=results/log_v3_c.txt setsid nohup bash run_tuning_v3_par.sh c > results/par_c.out 2>&1 < /dev/null & '
    'LOG=results/log_v3_d.txt setsid nohup bash run_tuning_v3_par.sh d > results/par_d.out 2>&1 < /dev/null & '
    'sleep 10; pgrep -af "run_tuning[_]v3_par" | wc -l'
)
print('worker 脚本进程数（应为4）:', run(cmd, t=40))
time.sleep(25)
print('--- GPU 进程（应逐渐到4）---')
print(run('nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader'))
print('--- 各日志尾部 ---')
print(run('tail -n 2 /hy-tmp/MambaStock/results/par_?.out /hy-tmp/MambaStock/results/log_v3_?.txt 2>/dev/null'))
c.close()
