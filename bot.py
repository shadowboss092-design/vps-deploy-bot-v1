from __future__ import annotations
import asyncio, logging, os, re, secrets, shutil, socket, sqlite3, string
from datetime import datetime, timezone
from pathlib import Path
import discord, psutil
from discord.ext import commands

NAME=os.getenv("BOT_NAME","SHADOW VPS")
PREFIX=os.getenv("PREFIX",".")
TOKEN=os.getenv("DISCORD_TOKEN","").strip()
ADMINS={x.strip() for x in os.getenv("MAIN_ADMIN_ID","").split(",") if x.strip()}
DB_PATH=os.getenv("DATABASE_PATH","/opt/evil-vps-bot/vps-v2.db")
POOL=os.getenv("DEFAULT_STORAGE_POOL","default")
IMAGE=os.getenv("DEFAULT_OS_IMAGE","ubuntu:22.04")
PUBLIC_IP=os.getenv("PUBLIC_IP","YOUR_SERVER_PUBLIC_IP")
RAM_RESERVE=int(os.getenv("RESERVE_RAM_GB","3"))
DISK_RESERVE=int(os.getenv("RESERVE_DISK_GB","15"))
CPU_RESERVE=int(os.getenv("RESERVE_CPU","2"))
TIMEOUT=int(os.getenv("CLAIM_TIMEOUT","900"))

TIERS={
"2":{"invites":2,"ram":1,"cpu":1,"disk":5,"name":"Bronze","icon":"🥉"},
"4":{"invites":4,"ram":2,"cpu":1,"disk":5,"name":"Silver","icon":"🥈"},
"6":{"invites":6,"ram":4,"cpu":1,"disk":10,"name":"Gold","icon":"🏅"},
"8":{"invites":8,"ram":6,"cpu":1,"disk":15,"name":"Trophy","icon":"🏆"},
"10":{"invites":10,"ram":8,"cpu":2,"disk":20,"name":"Diamond","icon":"💠"},
"14":{"invites":14,"ram":12,"cpu":3,"disk":25,"name":"Crown","icon":"👑"},
"18":{"invites":18,"ram":16,"cpu":3,"disk":30,"name":"Crystal","icon":"💎"},
"22":{"invites":22,"ram":20,"cpu":4,"disk":35,"name":"Fire","icon":"🔥"},
"26":{"invites":26,"ram":24,"cpu":4,"disk":40,"name":"Lightning","icon":"⚡"},
"32":{"invites":32,"ram":32,"cpu":6,"disk":45,"name":"Cosmic","icon":"💫"}}
REWARDS=[
"[🥉](https://discord.com/assets/21d7244670423a9b.svg) 𝟸 ɪɴᴠɪᴛᴇꜱ → 𝟷 ɢʙ ʀᴀᴍ · 𝟷 ᴠᴄᴏʀᴇ · 5 ɢʙ ɴᴠᴍᴇ",
"[🥈](https://discord.com/assets/e60f28f718ca79b5.svg) 𝟺 ɪɴᴠɪᴛᴇꜱ → 𝟸 ɢʙ ʀᴀᴍ · 𝟷 ᴠᴄᴏʀᴇ · 5 ɢʙ ɴᴠᴍᴇ",
"[🏅](https://discord.com/assets/697093c635cda7e1.svg) 𝟼 ɪɴᴠɪᴛᴇꜱ → 𝟺 ɢʙ ʀᴀᴍ · 𝟷 ᴠᴄᴏʀᴇ · 10 ɢʙ ɴᴠᴍᴇ",
"[🏆](https://discord.com/assets/f11aff9f1c8c5f19.svg) 𝟾 ɪɴᴠɪᴛᴇꜱ → 𝟼 ɢʙ ʀᴀᴍ · 𝟷 ᴠᴄᴏʀᴇ · 15 ɢʙ ɴᴠᴍᴇ",
"[💠](https://discord.com/assets/af8fe638d735931e.svg) 𝟷𝟶 ɪɴᴠɪᴛᴇꜱ → 𝟾 ɢʙ ʀᴀᴍ · 𝟸 ᴠᴄᴏʀᴇ · 20 ɢʙ ɴᴠᴍᴇ",
"[👑](https://discord.com/assets/b09a9a54f8e34d23.svg) 𝟷4 ɪɴᴠɪᴛᴇꜱ → 𝟷𝟸 ɢʙ ʀᴀᴍ · 𝟹 ᴠᴄᴏʀᴇ · 25 ɢʙ ɴᴠᴍᴇ",
"[💎](https://discord.com/assets/e1c130b994e082f2.svg) 18 ɪɴᴠɪᴛᴇꜱ → 𝟷𝟼 ɢʙ ʀᴀᴍ · 𝟹 ᴠᴄᴏʀᴇ · 30 ɢʙ ɴᴠᴍᴇ",
"[🔥](https://discord.com/assets/a7bd71d6389d0dfe.svg) 22 ɪɴᴠɪᴛᴇꜱ → 𝟸𝟶 ɢʙ ʀᴀᴍ · 𝟺 ᴠᴄᴏʀᴇ · 35 ɢʙ ɴᴠᴍᴇ",
"[⚡](https://discord.com/assets/d3aa5cc6245cf253.svg) 26 ɪɴᴠɪᴛᴇꜱ → 𝟸𝟺 ɢʙ ʀᴀᴍ · 𝟺 ᴠᴄᴏʀᴇ · 40 ɢʙ ɴᴠᴍᴇ",
"[💫](https://discord.com/assets/f512e11ede53f289.svg) 32 ɪɴᴠɪᴛᴇꜱ → 𝟹𝟸 ɢʙ ʀᴀᴍ · 𝟼 ᴠᴄᴏʀᴇ · 45 ɢʙ ɴᴠᴍᴇ"]

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s",
 handlers=[logging.StreamHandler(),logging.FileHandler("/opt/evil-vps-bot/bot-v2.log")])
log=logging.getLogger("shadow-vps-v2")
claim_lock=asyncio.Lock()
invite_cache={}

def connect_db():
 Path(DB_PATH).parent.mkdir(parents=True,exist_ok=True)
 c=sqlite3.connect(DB_PATH,timeout=30); c.row_factory=sqlite3.Row
 c.execute("PRAGMA journal_mode=WAL"); return c

def init_db():
 with connect_db() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS referrals(guild_id TEXT,invitee_id TEXT,inviter_id TEXT,code TEXT,joined_at TEXT,active INTEGER DEFAULT 1,consumed INTEGER DEFAULT 0,PRIMARY KEY(guild_id,invitee_id));
  CREATE INDEX IF NOT EXISTS referral_owner ON referrals(guild_id,inviter_id,active,consumed);
  CREATE TABLE IF NOT EXISTS claims(id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id TEXT,user_id TEXT,tier TEXT,spent INTEGER,instance TEXT UNIQUE,port INTEGER,created_at TEXT);
  CREATE TABLE IF NOT EXISTS instances(instance TEXT PRIMARY KEY,guild_id TEXT,user_id TEXT,ram INTEGER,cpu INTEGER,disk INTEGER,port INTEGER UNIQUE,created_at TEXT,status TEXT DEFAULT 'running');
  """)
init_db()

def is_admin(uid): return str(uid) in ADMINS

def counts(gid,uid):
 with connect_db() as c:
  r=c.execute("""SELECT SUM(active=1) active,SUM(active=1 AND consumed=0) available,SUM(consumed=1) used
  FROM referrals WHERE guild_id=? AND inviter_id=?""",(str(gid),str(uid))).fetchone()
 return tuple(int(r[k] or 0) for k in ("active","available","used"))

async def cmd(*args,timeout=180):
 p=await asyncio.create_subprocess_exec(*args,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
 try: out,err=await asyncio.wait_for(p.communicate(),timeout)
 except asyncio.TimeoutError:
  p.kill(); await p.wait(); raise RuntimeError("LXD command timed out.")
 if p.returncode: raise RuntimeError((err.decode(errors="replace") or out.decode(errors="replace"))[-1500:])
 return out.decode(errors="replace").strip()

def capacity(t):
 ram=psutil.virtual_memory().available/1024**3-RAM_RESERVE
 disk=shutil.disk_usage("/").free/1024**3-DISK_RESERVE
 cpu=max(1,(os.cpu_count() or 2)-CPU_RESERVE)
 with connect_db() as c: used=c.execute("SELECT COALESCE(SUM(cpu),0) FROM instances WHERE status='running'").fetchone()[0]
 if t["ram"]>max(0,ram): raise RuntimeError(f"Safe free RAM is only {max(0,ram):.1f} GB.")
 if t["disk"]>max(0,disk): raise RuntimeError(f"Safe free disk is only {max(0,disk):.1f} GB.")
 if used+t["cpu"]>cpu: raise RuntimeError(f"CPU allocation budget reached ({cpu} vCPU).")

def make_password():
 chars=string.ascii_letters+string.digits+"!@#%_-+="
 return "".join(secrets.choice(chars) for _ in range(24))

async def provision(uid,t):
 if PUBLIC_IP=="YOUR_SERVER_PUBLIC_IP": raise RuntimeError("Set PUBLIC_IP in bot.env before claims.")
 await cmd("lxc","info",timeout=20); await cmd("lxc","storage","show",POOL,timeout=20); capacity(t)
 name=f"shv2-{uid}-{datetime.now(timezone.utc).strftime('%y%m%d%H%M%S')}"
 pw=make_password(); port=0
 for p in range(22000,50000):
  try:
   with socket.socket() as s: s.bind(("0.0.0.0",p))
   port=p; break
  except OSError: continue
 if not port: raise RuntimeError("No free SSH proxy port.")
 made=False
 try:
  await cmd("lxc","launch",IMAGE,name,"-s",POOL,"-c",f"limits.memory={t['ram']}GB","-c",f"limits.cpu={t['cpu']}",timeout=TIMEOUT); made=True
  await cmd("lxc","config","device","set",name,"root","size",f"{t['disk']}GB",timeout=30)
  script=("export DEBIAN_FRONTEND=noninteractive; apt-get update -y && apt-get install -y openssh-server; "
   f"echo 'root:{pw}' | chpasswd; mkdir -p /run/sshd; "
   "printf '\nPermitRootLogin yes\nPasswordAuthentication yes\n' >> /etc/ssh/sshd_config; systemctl enable --now ssh")
  await cmd("lxc","exec",name,"--","bash","-lc",script,timeout=TIMEOUT)
  out=await cmd("lxc","list",name,"-c","4","--format","csv",timeout=30)
  m=re.search(r"(?:10|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}",out)
  if not m: raise RuntimeError("No private IPv4 address found.")
  await cmd("lxc","config","device","add",name,f"ssh-{port}","proxy",f"listen=tcp:0.0.0.0:{port}",f"connect=tcp:{m.group(0)}:22",timeout=30)
  return name,pw,port
 except Exception:
  if made:
   try: await cmd("lxc","delete",name,"--force",timeout=90)
   except Exception: log.exception("Cleanup failed for %s",name)
  raise

intents=discord.Intents.default(); intents.guilds=True; intents.members=True; intents.message_content=True
bot=commands.Bot(command_prefix=PREFIX,intents=intents,help_command=None)

async def refresh(g):
 try: invite_cache[g.id]={i.code:i for i in await g.invites()}
 except discord.Forbidden: log.warning("Bot needs Manage Server permission in guild %s",g.id)
 except discord.HTTPException: log.exception("Invite refresh failed")

@bot.event
async def on_ready():
 for g in bot.guilds: await refresh(g)
 await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name=f"{PREFIX}claim | VPS Rewards"))
 log.info("%s online as %s",NAME,bot.user)

@bot.event
async def on_guild_join(g): await refresh(g)

@bot.event
async def on_invite_create(inv):
 if inv.guild: await refresh(inv.guild)

@bot.event
async def on_invite_delete(inv):
 if inv.guild: await refresh(inv.guild)

@bot.event
async def on_member_join(m):
 if m.bot: return
 before=invite_cache.get(m.guild.id,{})
 try:
  after={i.code:i for i in await m.guild.invites()}
  used=next((i for code,i in after.items() if code in before and (i.uses or 0)>(before[code].uses or 0)),None)
  invite_cache[m.guild.id]=after
  if used and used.inviter and used.inviter.id!=m.id:
   with connect_db() as c:
    c.execute("INSERT OR IGNORE INTO referrals(guild_id,invitee_id,inviter_id,code,joined_at,active,consumed) VALUES(?,?,?,?,?,1,0)",
     (str(m.guild.id),str(m.id),str(used.inviter.id),used.code,datetime.now(timezone.utc).isoformat()))
 except discord.Forbidden: log.warning("Invite tracking unavailable: grant Manage Server permission.")
 except discord.HTTPException: log.exception("Invite attribution failed")

@bot.event
async def on_member_remove(m):
 with connect_db() as c: c.execute("UPDATE referrals SET active=0 WHERE guild_id=? AND invitee_id=?",(str(m.guild.id),str(m.id)))
 await refresh(m.guild)

def reward_embed():
 e=discord.Embed(title="🎁 Invite Rewards",description="Invite members and redeem credits for a VPS. Choose a plan below.",color=discord.Color.blurple())
 e.description+="\n\n"+"\n".join(REWARDS)
 e.set_footer(text="Unique human invites only. Members who leave no longer count.")
 return e

class RewardSelect(discord.ui.Select):
 def __init__(self,uid,gid):
  self.uid,self.gid=uid,gid
  opts=[discord.SelectOption(label=f"{t['name']} • {t['ram']}GB RAM / {t['cpu']} vCore",value=k,description=f"{t['invites']} invites • {t['disk']}GB NVMe",emoji=t["icon"]) for k,t in TIERS.items()]
  super().__init__(placeholder="Select your VPS plan",min_values=1,max_values=1,options=opts)
 async def callback(self,i):
  if i.user.id!=self.uid:
   await i.response.send_message("This menu belongs to another member.",ephemeral=True); return
  key=self.values[0]; t=TIERS[key]
  await i.response.defer(ephemeral=True,thinking=True)
  async with claim_lock:
   _,available,_=counts(self.gid,self.uid)
   if available<t["invites"]:
    await i.followup.send(f"You need {t['invites']} available invites; you have {available}.",ephemeral=True); return
   try:
    name,pw,port=await provision(self.uid,t); now=datetime.now(timezone.utc).isoformat()
    with connect_db() as c:
     refs=c.execute("SELECT invitee_id FROM referrals WHERE guild_id=? AND inviter_id=? AND active=1 AND consumed=0 ORDER BY joined_at LIMIT ?",
      (str(self.gid),str(self.uid),t["invites"])).fetchall()
     if len(refs)!=t["invites"]: raise RuntimeError("Invite balance changed. Contact an admin.")
     c.executemany("UPDATE referrals SET consumed=1 WHERE guild_id=? AND invitee_id=? AND inviter_id=? AND active=1 AND consumed=0",
      [(str(self.gid),r["invitee_id"],str(self.uid)) for r in refs])
     c.execute("INSERT INTO claims(guild_id,user_id,tier,spent,instance,port,created_at) VALUES(?,?,?,?,?,?,?)",
      (str(self.gid),str(self.uid),key,t["invites"],name,port,now))
     c.execute("INSERT INTO instances(instance,guild_id,user_id,ram,cpu,disk,port,created_at,status) VALUES(?,?,?,?,?,?,?,?, 'running')",
      (name,str(self.gid),str(self.uid),t["ram"],t["cpu"],t["disk"],port,now))
    e=discord.Embed(title="✅ VPS Deployed",description=f"Your {t['name']} VPS is ready.",color=discord.Color.green())
    e.add_field(name="Resources",value=f"{t['ram']} GB RAM\n{t['cpu']} vCore\n{t['disk']} GB NVMe")
    e.add_field(name="SSH login",value=f"Host: {PUBLIC_IP}\nPort: {port}\nUser: root\nPassword: ||{pw}||",inline=False)
    e.add_field(name="Instance",value=name,inline=False)
    e.set_footer(text=f"{t['invites']} credits consumed after successful deployment.")
    await i.followup.send(embed=e,ephemeral=True)
    try: await i.user.send(embed=e)
    except discord.Forbidden: pass
   except Exception as ex:
    log.exception("Claim failed for %s",self.uid)
    await i.followup.send(f"VPS deployment failed. No invite credits were deducted.\n{str(ex)[:1200]}",ephemeral=True)

class ClaimView(discord.ui.View):
 def __init__(self,uid,gid):
  super().__init__(timeout=180); self.add_item(RewardSelect(uid,gid))

@bot.command(name="claim")
@commands.guild_only()
async def claim(ctx):
 e=reward_embed(); e.add_field(name="Available credits",value=str(counts(ctx.guild.id,ctx.author.id)[1]),inline=False)
 await ctx.send(embed=e,view=ClaimView(ctx.author.id,ctx.guild.id))

@bot.command(name="invites",aliases=["invs"])
@commands.guild_only()
async def invites(ctx):
 active,available,used=counts(ctx.guild.id,ctx.author.id)
 e=discord.Embed(title="📨 Your Invite Stats",color=discord.Color.blurple())
 e.add_field(name="Active referrals",value=str(active),inline=True)
 e.add_field(name="Available credits",value=str(available),inline=True)
 e.add_field(name="Credits used",value=str(used),inline=True)
 await ctx.send(embed=e)

@bot.command(name="myvps")
@commands.guild_only()
async def myvps(ctx):
 with connect_db() as c:
  rows=c.execute("SELECT instance,ram,cpu,disk,port,status FROM instances WHERE guild_id=? AND user_id=? ORDER BY created_at DESC",(str(ctx.guild.id),str(ctx.author.id))).fetchall()
 if not rows: await ctx.send("No VPS yet. Use .claim to redeem invite rewards."); return
 e=discord.Embed(title="🖥️ Your VPS Instances",color=discord.Color.blurple())
 for r in rows[:10]: e.add_field(name=r["instance"],value=f"{r['ram']} GB RAM • {r['cpu']} vCore • {r['disk']} GB NVMe\nSSH port: {r['port']} • {r['status']}",inline=False)
 await ctx.send(embed=e)

@bot.command(name="ping")
async def ping(ctx): await ctx.send(f"Pong! {round(bot.latency*1000)}ms")

@bot.command(name="help")
async def help_cmd(ctx):
 e=discord.Embed(title=f"{NAME} Commands",color=discord.Color.blurple())
 e.add_field(name="Members",value=".claim — VPS reward menu\n.invites — Invite balance\n.myvps — Your VPS list\n.ping — Latency",inline=False)
 if is_admin(ctx.author.id): e.add_field(name="Admins",value=".syncinvites — Refresh invite cache\n.vpslist — List recent VPS",inline=False)
 await ctx.send(embed=e)

@bot.command(name="syncinvites")
@commands.guild_only()
async def syncinvites(ctx):
 if not is_admin(ctx.author.id): await ctx.send("Not authorized."); return
 await refresh(ctx.guild); await ctx.send("Invite cache refreshed. Existing members are not retroactively credited.")

@bot.command(name="vpslist")
@commands.guild_only()
async def vpslist(ctx):
 if not is_admin(ctx.author.id): await ctx.send("Not authorized."); return
 with connect_db() as c: rows=c.execute("SELECT instance,user_id,ram,cpu,disk,port FROM instances ORDER BY created_at DESC LIMIT 25").fetchall()
 if not rows: await ctx.send("No VPS claimed yet."); return
 await ctx.send("\n".join(f"{r['instance']} — <@{r['user_id']}> — {r['ram']}GB/{r['cpu']}vC/{r['disk']}GB — port {r['port']}" for r in rows))

@bot.event
async def on_command_error(ctx,error):
 if isinstance(error,commands.CommandNotFound): return
 if isinstance(error,commands.NoPrivateMessage): await ctx.send("Use this command in your Discord server."); return
 log.error("Command error: %s",error,exc_info=(type(error),error,error.__traceback__))
 await ctx.send("Command failed. Please contact an administrator.")

if __name__=="__main__":
 if not TOKEN: raise SystemExit("DISCORD_TOKEN is missing.")
 if not ADMINS or any(not x.isdigit() for x in ADMINS): raise SystemExit("MAIN_ADMIN_ID must contain numeric Discord IDs.")
 bot.run(TOKEN,log_handler=None)
