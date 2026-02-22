import subprocess
import sys
import os
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def start_bot():
    return subprocess.Popen(
        [sys.executable, "main.py", "--worker"], 
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )

def main_manager():
    bot_process = start_bot()
    
    while True:
        clear_screen()
        print("===============================")
        print("      CollapseBot Manager      ")
        print("===============================")
        status = "RUNNING" if bot_process.poll() is None else "STOPPED"
        print(f" Status: {status}")
        print("-------------------------------")
        print(" 1. Restart bot")
        print(" 2. Stop bot")
        print(" 3. Start bot (if stopped)")
        print(" 4. Exit Manager & Bot")
        print("===============================")
        
        choice = input("Select option: ")
        
        if choice == '1':
            if bot_process.poll() is None:
                bot_process.terminate()
                bot_process.wait()
            bot_process = start_bot()
            time.sleep(1)
            
        elif choice == '2':
            if bot_process.poll() is None:
                bot_process.terminate()
            time.sleep(1)
            
        elif choice == '3':
            if bot_process.poll() is not None:
                bot_process = start_bot()
            time.sleep(1)
            
        elif choice == '4':
            if bot_process.poll() is None:
                bot_process.terminate()
            break

if __name__ == "__main__":
    try:
        main_manager()
    except KeyboardInterrupt:
        pass
