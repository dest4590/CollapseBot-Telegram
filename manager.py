# Manager for CollapseBot
# Author: W1xced, updated by Antigravity
# Version: 2.5
# Description: A robust manager for CollapseBot, featuring live log streaming, real-time analytics, and enhanced process safety for stable operation.

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

def cleanup():
    global _current_bot_process
    if _current_bot_process and _current_bot_process.poll() is None:
        try:
            _current_bot_process.terminate()
            _current_bot_process.wait(timeout=2)
        except Exception:
            try:
                _current_bot_process.kill()
            except Exception:
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
    
    status_table.add_row("Bot Service Layer :", f"[{status_color}]{status_text}[/]")
    status_table.add_row("Interpreter Engine :", f"[dim #CAF0F8]{escape(sys.version.split()[0])}[/]")
    status_table.add_row("Working Directory :", f"[dim #CAF0F8]{escape(os.path.basename(os.getcwd()))}[/]")

    controls = Table(box=box.MINIMAL, expand=True, show_header=False, border_style="#00B4D8")
    controls.add_column("Col1", justify="left")
    controls.add_column("Col2", justify="left")
    controls.add_column("Col3", justify="left")
    
    controls.add_row(
        "🚀 [bold #00FF7F][ 1 ] START ENGINE[/]",
        "📜 [bold #9370DB][ 4 ] LIVE LOGS[/]",
        ""
    )
    controls.add_row(
        "⏸️ [bold #FF3366][ 2 ] HALT ENGINE[/]",
        "📊 [bold #FFA500][ 5 ] ANALYTICS[/]",
        ""
    )
    controls.add_row(
        "🔄 [bold #FFD700][ 3 ] REBOOT SYSTEM[/]",
        "🚪 [bold #FF00FF][ 6 ] EXIT[/]",
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
    
    try:
        while True:
            clear_screen()
            console.print(draw_interface(bot_process))
            
            choice = console.input("  [bold #00D4FF]❯❯ Select Operation:[/] ")
            
            if choice == '1':
                if bot_process.poll() is not None:
                    with console.status("[bold #00FF7F]Initializing Bot Core...[/]"):
                        bot_process = start_bot()
                        time.sleep(1.5)
                else:
                    console.print("  [bold #FFD700]⚠️ Bot is already active![/]")
                    time.sleep(1)
                    
            elif choice == '2':
                if bot_process.poll() is None: 
                    with console.status("[bold #FF3366]Shutting down Bot Core...[/]"):
                        bot_process.terminate()
                        time.sleep(1.5)
                else:
                    console.print("  [bold #FFD700]⚠️ Bot is already halted![/]")
                    time.sleep(1)
                    
            elif choice == '3':
                with console.status("[bold #FFD700]Rebooting system...[/]"):
                    if bot_process.poll() is None:
                        bot_process.terminate()
                        bot_process.wait()
                    bot_process = start_bot()
                    time.sleep(1.5)
                    
            elif choice == '4':
                clear_screen()
                console.print(Panel("[bold #9370DB]🟢 LIVE ENGINE LOGS[/]\n[dim]Press ANY KEY to return to the main menu...[/]", border_style="#9370DB"))
                
                import msvcrt
                # Выводим последние 30 строк из имеющейся истории
                snapshot = list(full_logs)
                for line in snapshot[-30:]:
                    console.print(line)
                
                last_seen_total = log_counter
                
                while True:
                    if msvcrt.kbhit():
                        msvcrt.getch()
                        break
                    
                    if log_counter > last_seen_total:
                        # Если пришли новые строки, печатаем их
                        new_lines_count = log_counter - last_seen_total
                        # Чтобы индекс не вышел за границы deque (500), берем минимум
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
                stats_table.add_row("Engines Spawned :", str(stats["engines_spawned"]))
                stats_table.add_row("Bot Starts (/start) :", str(bot_stats.get("start_count", 0)))
                stats_table.add_row("Snippets Searched :", str(bot_stats.get("snippet_searches", 0)))
                stats_table.add_row("System Health :", "[bold #00FF7F]EXCELLENT[/]")
                
                stats_panel = Panel(
                    Align.center(stats_table),
                    title="[bold #FFA500] SESSION ANALYTICS [/]",
                    border_style="#FFA500",
                    padding=(1, 4)
                )
                console.print(stats_panel)
                console.input("\n  [dim]Press ENTER to return...[/]")
                
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
