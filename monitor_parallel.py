# 并行调参监视器：每 2 分钟轮询远程 4 路 worker 进度，全部完成则退出（触发后台任务完成通知）
import os, paramiko, time, sys

HOST, PORT, PW = 'i-1.gpushare.com', 29582, os.environ['HY_PW']
LOGS = {'a': 'results/experiment_log_v3_tuning.txt', 'b': 'results/log_v3_b.txt',
        'c': 'results/log_v3_c.txt', 'd': 'results/log_v3_d.txt'}
# 各路预期组数：a=601288共20(已完成7)、b=601328共20、c=601988共20、d=面板共20
EXPECT = {'a': 20, 'b': 20, 'c': 20, 'd': 20}

t0 = time.time()
while True:
    try:
        c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(HOST, port=PORT, username='root', password=PW, timeout=20)
        all_done = True
        stat = []
        for k, lg in LOGS.items():
            _, o, _ = c.exec_command(
                f"grep -c '^  DA' /hy-tmp/MambaStock/{lg} 2>/dev/null; "
                f"grep -c 'ALL DONE' /hy-tmp/MambaStock/{lg} 2>/dev/null")
            lines = o.read().decode().split()
            n = int(lines[0]) if lines and lines[0].isdigit() else 0
            fin = len(lines) > 1 and lines[1] != '0'
            if k == 'a':  # 主日志里含 600036 的 20 组，只看增量
                n -= 20
            stat.append(f'{k}:{n}/{EXPECT[k]}' + ('✓' if fin else ''))
            all_done = all_done and fin
        c.close()
        print(f'[{time.time()-t0:5.0f}s] ' + '  '.join(stat), flush=True)
        if all_done:
            print('PARALLEL ALL DONE', flush=True)
            sys.exit(0)
    except Exception as ex:
        print(f'[{time.time()-t0:5.0f}s] poll error: {ex}', flush=True)
    time.sleep(120)
