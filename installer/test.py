import sys
import tty
import termios

def input_password():
    print("Enter Password: (Press tab to show/hide input)")
    fd = sys.stdin.fileno()
    oldTtyAttr = termios.tcgetattr(fd)
    password = ""
    visible = False
    try:
        tty.setraw(fd)
        while True:
            oldPassLength = len(password)
            char = sys.stdin.read(1)
            if char == "\n" or char == "\r": # Submit input
                break
            elif char == "\t": # Toggle visiblity
                visible = not visible
            elif char == "\x7f": # Backspace
                if len(password) == 0:
                    continue
                password = password[:-1]
            elif char.isprintable(): # Character typed
                password += char
            else: # Invalid character
                raise KeyboardInterrupt
            sys.stdout.write("\r" + (" " * oldPassLength) + "\r" + (password if visible else ("*" * len(password))))
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, oldTtyAttr)
        print()
    return password

passwd = input_password()
print(f"You entered: {passwd}")