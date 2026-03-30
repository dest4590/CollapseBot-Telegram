import subprocess
import sys
import os
import time
import ctypes
import ctypes.wintypes
import threading
from collections import deque
import json
import atexit
import signal

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich import box
    from rich.align import Align
    from rich.style import Style
    from rich.markup import escape
except ImportError:
    print("Installing required UI packages...")
    subprocess.call([sys.executable, "-m", "pip", "install", "rich"])
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich import box
    from rich.align import Align
    from rich.style import Style
    from rich.markup import escape

console = Console()
log_buffer = deque(maxlen=20)
full_logs = deque(maxlen=500)
log_counter = 0
stats = {"start_time": time.time(), "engines_spawned": 0, "errors": 0}

def log_reader(pipe):
    global log_counter
    try:
        for line in iter(pipe.readline, ''):
            if not line: break
            decoded = line.strip()
            log_buffer.append(decoded)
            full_logs.append(decoded)
            log_counter += 1
    except Exception:
        pass
    pipe.close()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

_current_bot_process = None
_current_tunnel_process = None
_tunnel_url = "Not Started"

def update_env_url(url):
    try:
        if os.path.exists(".env"):
            with open(".env", "r", encoding="utf-8") as f:
                content = f.read()
            import re
            new_content = re.sub(r'(?m)^WEBAPP_URL=.*$', '', content).strip()
            new_content += f'\nWEBAPP_URL={url}\n'
            with open(".env", "w", encoding="utf-8") as f:
                f.write(new_content)
        else:
            with open(".env", "w", encoding="utf-8") as f:
                f.write(f'WEBAPP_URL={url}\n')
    except Exception as e:
        full_logs.append(f"Failed to update .env: {e}")

def tunnel_reader(pipe):
    global log_counter, _tunnel_url
    import re
    try:
        for line in iter(pipe.readline, ''):
            if not line: break
            decoded = line.strip()
            full_logs.append("[TUNNEL] " + decoded)
            log_counter += 1
            
            match = re.search(r'(https://[a-zA-Z0-9-]+\.lhr\.life|https://[a-zA-Z0-9-]+\.serveo\.net|https://[a-zA-Z0-9-]+\.serveousercontent\.com)', decoded)
            if match:
                _tunnel_url = match.group(1)
                update_env_url(_tunnel_url)
    except Exception:
        pass
    pipe.close()

def start_tunnel():
    global _current_tunnel_process, _tunnel_url
    if _current_tunnel_process and _current_tunnel_process.poll() is None:
        try:
            _current_tunnel_process.terminate()
        except:
            pass
            
    _tunnel_url = "Connecting..."
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:127.0.0.1:8085", "nokey@localhost.run"]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        stdin=subprocess.DEVNULL,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0
    )
    _current_tunnel_process = process
    threading.Thread(target=tunnel_reader, args=(process.stdout,), daemon=True).start()

def cleanup():
    global _current_bot_process, _current_tunnel_process
    if _current_bot_process and _current_bot_process.poll() is None:
        try:
            _current_bot_process.terminate()
            _current_bot_process.wait(timeout=2)
        except Exception:
            try:
                _current_bot_process.kill()
            except Exception:
                pass
                
    if _current_tunnel_process and _current_tunnel_process.poll() is None:
        try:
            _current_tunnel_process.terminate()
            _current_tunnel_process.wait(timeout=2)
        except:
            try:
                _current_tunnel_process.kill()
            except:
                pass

atexit.register(cleanup)

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def start_bot():
    global _current_bot_process
    process = subprocess.Popen(
        [sys.executable, "main.py", "--worker"], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    _current_bot_process = process
    threading.Thread(target=log_reader, args=(process.stdout,), daemon=True).start()
    stats["engines_spawned"] += 1
    return process

def draw_interface(bot_process):
    is_running = bot_process.poll() is None
    status_color = "#00FF7F" if is_running else "#FF3366" 
    status_text = "● ONLINE & LISTENING" if is_running else "○ OFFLINE"

    logo_raw = [
        " ██████╗  ██████╗  ██╗      ██╗        █████╗   ██████╗   ███████╗  ███████╗ ",
        "██╔════╝ ██╔═══██╗ ██║      ██║       ██╔══██╗  ██╔══██╗  ██╔════╝  ██╔════╝ ",
        "██║      ██║   ██║ ██║      ██║       ███████║  ██████╔╝  ███████╗  █████╗   ",
        "██║      ██║   ██║ ██║      ██║       ██╔══██║  ██╔═══╝   ╚════██║  ██╔══╝   ",
        "╚██████╗ ╚██████╔╝ ███████╗ ███████╗  ██║  ██║  ██║       ███████║  ███████╗ ",
        " ╚═════╝  ╚═════╝  ╚══════╝ ╚══════╝  ╚═╝  ╚═╝  ╚═╝       ╚══════╝  ╚══════╝ "
    ]
    logo = "\n".join(logo_raw)
    header_text = Align.center(Text(logo, style="bold #00D4FF"))
    
    status_table = Table(
        box=box.ROUNDED, 
        show_header=False, 
        expand=True, 
        border_style="#0077B6",
        padding=(0, 2)
    )
    status_table.add_column("Key", style="bold #90E0EF", justify="right", width=25)
    status_table.add_column("Value", style="bold white", justify="left")
    
    status_table.add_row("Bot Status :", f"[{status_color}]{status_text}[/]")
    status_table.add_row("WebApp Tunnel :", f"[bold #00FF7F]{escape(_tunnel_url)}[/]")
    status_table.add_row("Python Version :", f"[dim #CAF0F8]{escape(sys.version.split()[0])}[/]")
    status_table.add_row("Working Directory :", f"[dim #CAF0F8]{escape(os.path.basename(os.getcwd()))}[/]")

    controls = Table(box=box.MINIMAL, expand=True, show_header=False, border_style="#00B4D8")
    controls.add_column("Col1", justify="left")
    controls.add_column("Col2", justify="left")
    controls.add_column("Col3", justify="left")
    
    controls.add_row(
        "[bold #00FF7F][ 1 ] START BOT[/]",
        "[bold #9370DB][ 4 ] LIVE LOGS[/]",
        ""
    )
    controls.add_row(
        "[bold #FF3366][ 2 ] STOP BOT[/]",
        "[bold #FFA500][ 5 ] STATISTICS[/]",
        ""
    )
    controls.add_row(
        "[bold #FFD700][ 3 ] RESTART BOT[/]",
        "[bold #FF00FF][ 6 ] EXIT[/]",
        ""
    )

    layout = Table.grid(expand=True)
    layout.add_row(Align.center(header_text))
    
    glass_status = Panel(
        status_table, 
        border_style="#0096C7", 
        title="[bold #CAF0F8] SYSTEM MONITOR [/]",
        subtitle="[dim #0096C7] ── Collapse Architecture ── [/]",
        padding=(0, 4)
    )
    layout.add_row(glass_status)
    
    glass_controls = Panel(
        Align.center(controls), 
        border_style="#00B4D8", 
        title="[bold #90E0EF] ACTION CENTER [/]",
        padding=(0, 0)
    )
    layout.add_row(glass_controls)

    return Panel(
        layout, 
        border_style="bold #00D4FF", 
        box=box.DOUBLE_EDGE,
        padding=(0, 2)
    )

def get_bot_stats():
    try:
        if os.path.exists("stats.json"):
            with open("stats.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"start_count": 0, "snippet_searches": 0}

def main_manager():
    bot_process = start_bot()
    start_tunnel()
    
    import msvcrt
    global _tunnel_url
    last_tunnel_url = _tunnel_url
    
    try:
        while True:
            last_bot_status = bot_process.poll() is None
            
            clear_screen()
            console.print(draw_interface(bot_process))
            console.print("  [bold #00D4FF]❯❯ Select Operation (1-6):[/] ", end="")
            sys.stdout.flush()
            
            choice = None
            while True:
                if msvcrt.kbhit():
                    char = msvcrt.getch().decode('utf-8', errors='ignore')
                    if char in ['1', '2', '3', '4', '5', '6']:
                        choice = char
                        print(choice) 
                        time.sleep(0.2)
                        break
                
                current_running = bot_process.poll() is None
                if _tunnel_url != last_tunnel_url or current_running != last_bot_status:
                    last_tunnel_url = _tunnel_url
                    break
                    
                time.sleep(0.1)
                
            if choice is None:
                continue 
            
            if choice == '1':
                if bot_process.poll() is not None:
                    with console.status("[bold #00FF7F]Starting Bot...[/]"):
                        bot_process = start_bot()
                        time.sleep(1.5)
                else:
                    console.print("  [bold #FFD700]Bot is already active![/]")
                    time.sleep(1)
                    
            elif choice == '2':
                if bot_process.poll() is None: 
                    with console.status("[bold #FF3366]Stopping Bot...[/]"):
                        bot_process.terminate()
                        time.sleep(1.5)
                else:
                    console.print("  [bold #FFD700]Bot is already halted![/]")
                    time.sleep(1)
                    
            elif choice == '3':
                with console.status("[bold #FFD700]Restarting Bot...[/]"):
                    if bot_process.poll() is None:
                        bot_process.terminate()
                        bot_process.wait()
                    bot_process = start_bot()
                    start_tunnel()
                    time.sleep(1.5)
                    
            elif choice == '4':
                clear_screen()
                console.print(Panel("[bold #9370DB]LIVE BOT LOGS[/]\n[dim]Press ANY KEY to return to the main menu...[/]", border_style="#9370DB"))
                
                import msvcrt
                snapshot = list(full_logs)
                for line in snapshot[-30:]:
                    console.print(line)
                
                last_seen_total = log_counter
                
                # Очищаем буфер от случайных нажатий (например Enter)
                while msvcrt.kbhit():
                    msvcrt.getch()
                
                while True:
                    if msvcrt.kbhit():
                        msvcrt.getch()
                        break
                    
                    if log_counter > last_seen_total:
                        new_lines_count = log_counter - last_seen_total
                        actual_to_print = min(new_lines_count, len(full_logs))
                        current_all_logs = list(full_logs)
                        for i in range(len(current_all_logs) - actual_to_print, len(current_all_logs)):
                            console.print(current_all_logs[i])
                        last_seen_total = log_counter
                    
                    time.sleep(0.1)
                
            elif choice == '5':
                clear_screen()
                uptime = time.strftime("%Hh %Mm %Ss", time.gmtime(time.time() - stats["start_time"]))
                bot_stats = get_bot_stats()
                
                stats_table = Table(box=box.ROUNDED, show_header=False, border_style="#FFA500")
                stats_table.add_row("Session Uptime :", uptime)
                stats_table.add_row("Bot Restarts :", str(stats["engines_spawned"]))
                stats_table.add_row("Bot Starts (/start) :", str(bot_stats.get("start_count", 0)))
                stats_table.add_row("Snippets Searched :", str(bot_stats.get("snippet_searches", 0)))
                stats_table.add_row("Bot Health :", "[bold #00FF7F]OK[/]")
                
                stats_panel = Panel(
                    Align.center(stats_table),
                    title="[bold #FFA500] STATISTICS [/]",
                    border_style="#FFA500",
                    padding=(1, 4)
                )
                console.print(stats_panel)
                console.print("\n  [dim]Press ANY KEY to return...[/]")
                import msvcrt
                while msvcrt.kbhit(): msvcrt.getch()
                while not msvcrt.kbhit(): time.sleep(0.05)
                msvcrt.getch()
                
            elif choice == '6':
                cleanup()
                console.print("\n  [bold #FF00FF]Session Terminated. Goodbye.[/]")
                break
    finally:
        cleanup()

if __name__ == "__main__":
    try:
        main_manager()
    except (KeyboardInterrupt, SystemExit):
        cleanup()
        sys.exit(0)
