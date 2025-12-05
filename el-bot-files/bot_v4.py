#!/usr/bin/env python3
import os,logging,asyncio
from datetime import datetime
from pathlib import Path
from telegram import Update,BotCommand
from telegram.ext import Application,CommandHandler,MessageHandler,filters,ContextTypes
import httpx

TELEGRAM_TOKEN=os.getenv('TELEGRAM_BOT_TOKEN')
GITHUB_TOKEN=os.getenv('GITHUB_TOKEN')
ADMIN_ID=int(os.getenv('TELEGRAM_ADMIN_ID','0'))
TASKS_DIR=Path(os.getenv('AGENT_TASKS_DIR','/home/flomaster/agent-tasks'))
DOCKER_CONTAINER='claude-agent'
DOCKER_WORKSPACE='/home/ubuntu/workspace/errorlens'

logging.basicConfig(format='%(asctime)s-%(name)s-%(levelname)s-%(message)s',level=logging.INFO)
logger=logging.getLogger(__name__)
agent_state={"running":False,"task_name":None,"start_time":None,"log_file":None}

def is_admin(u):return u==ADMIN_ID

async def ensure_container():
    try:
        p=await asyncio.create_subprocess_exec('ssh','-i','/ssh/id_ed25519','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','flomaster@192.168.1.74','docker ps|grep claude-agent',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        o,_=await p.communicate()
        if p.returncode==0 and o:return True
        p=await asyncio.create_subprocess_exec('ssh','-i','/ssh/id_ed25519','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','flomaster@192.168.1.74','cd ~/projects/claude-agent&&docker-compose up -d',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        await p.communicate();await asyncio.sleep(3);return True
    except:return False

async def get_output(n=20):
    if not agent_state["log_file"]:return"No log"
    try:
        p=await asyncio.create_subprocess_exec('ssh','-i','/ssh/id_ed25519','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','flomaster@192.168.1.74',f"tail -{n} {agent_state['log_file']} 2>/dev/null",stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        o,_=await asyncio.wait_for(p.communicate(),timeout=10)
        return o.decode().strip()if o else"No output"
    except:return"Error"

async def start(u:Update,c:ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):await u.message.reply_text('Access denied');return
    await u.message.reply_text('EL_Bot v4\n/exec - run\n/status - status\n/tasks - list')

async def status(u:Update,c:ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):return
    if not agent_state["running"]:await u.message.reply_text('Agent:Not running');return
    e=(datetime.now()-agent_state["start_time"]).total_seconds()
    o=await get_output(10)
    await u.message.reply_text(f"Running {int(e/60)}m\n{o[-2000:]}")

async def tasks(u:Update,c:ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):return
    TASKS_DIR.mkdir(parents=True,exist_ok=True)
    t=sorted(TASKS_DIR.glob('*.md'),key=lambda x:x.stat().st_mtime,reverse=True)
    if not t:await u.message.reply_text('No tasks');return
    await u.message.reply_text('Tasks:\n'+'\n'.join([f"{i}.{x.name}"for i,x in enumerate(t[:10],1)]))

async def exec_task(u:Update,c:ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):return
    if agent_state["running"]:await u.message.reply_text(f"Running:{agent_state['task_name']}");return
    TASKS_DIR.mkdir(parents=True,exist_ok=True)
    t=sorted(TASKS_DIR.glob('*.md'),key=lambda x:x.stat().st_mtime,reverse=True)
    if not t:await u.message.reply_text('No tasks');return
    if not c.args:
        await u.message.reply_text('Select:\n'+'\n'.join([f"{i}.{x.name}"for i,x in enumerate(t[:10],1)]))
        c.user_data["waiting_exec"]=True;return
    idx=int(c.args[0])-1
    if idx<0 or idx>=len(t):await u.message.reply_text('Invalid');return
    tf=t[idx]
    m=await u.message.reply_text(f"Starting:{tf.name}")
    if not await ensure_container():await m.edit_text('Container failed');return
    lf=f"/tmp/agent-{datetime.now().strftime('%H%M%S')}.log"
    pr=f"Read .claude/settings.local.json then execute:/home/ubuntu/tasks/{tf.name}"
    cmd=f"docker exec {DOCKER_CONTAINER} bash -c 'cd {DOCKER_WORKSPACE}&&proxychains4 claude -p \"{pr}\"'"
    p=await asyncio.create_subprocess_exec('ssh','-i','/ssh/id_ed25519','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','flomaster@192.168.1.74',f"nohup {cmd}>{lf} 2>&1&echo $!",stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    o,_=await p.communicate()
    agent_state["running"]=True;agent_state["task_name"]=tf.name;agent_state["start_time"]=datetime.now();agent_state["log_file"]=lf
    await m.edit_text(f"Started PID:{o.decode().strip()}\nUse/status")
    asyncio.create_task(monitor(u.effective_chat.id,c,tf))

async def monitor(cid,c,tf):
    last=datetime.now()
    while agent_state["running"]:
        await asyncio.sleep(10)
        p=await asyncio.create_subprocess_exec('ssh','-i','/ssh/id_ed25519','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','flomaster@192.168.1.74','pgrep -f docker.exec.*claude-agent||echo done',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        o,_=await p.communicate()
        e=(datetime.now()-agent_state["start_time"]).total_seconds()
        if"done"in o.decode()or e>600:
            out=await get_output(30)
            await c.bot.send_message(chat_id=cid,text=f"Done!\n{out[-3000:]}")
            try:tf.unlink()
            except:pass
            agent_state["running"]=False;return
        if(datetime.now()-last).total_seconds()>=60:
            out=await get_output(5)
            await c.bot.send_message(chat_id=cid,text=f"Update{int(e/60)}m:\n{out[-1000:]}")
            last=datetime.now()

async def quick(u:Update,c:ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):return
    txt=u.message.text.strip()
    if c.user_data.get("waiting_exec")and txt.isdigit():
        c.user_data["waiting_exec"]=False;c.args=[txt]
        await exec_task(u,c)

async def post_init(app):
    await app.bot.set_my_commands([BotCommand('exec','Run'),BotCommand('status','Status'),BotCommand('tasks','List')])
    TASKS_DIR.mkdir(parents=True,exist_ok=True)

def main():
    app=Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler('start',start))
    app.add_handler(CommandHandler('exec',exec_task))
    app.add_handler(CommandHandler('status',status))
    app.add_handler(CommandHandler('tasks',tasks))
    app.add_handler(MessageHandler(filters.TEXT&~filters.COMMAND,quick))
    app.run_polling()

if __name__=='__main__':main()
