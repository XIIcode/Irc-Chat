import os
import random
import socket
import sys
import threading
import time

# ==========================================
# STANDARD SERVER LOGIC
# ==========================================


def handle_client(client_socket, clients, usernames):
  try:
    username = client_socket.recv(1024).decode("utf-8")
    usernames[client_socket] = username
    broadcast(f"*** {username} has joined the chat. ***", client_socket, clients, usernames)

    while True:
      message = client_socket.recv(1024)
      if not message:
        break
      msg_str = message.decode("utf-8").strip()

      if msg_str.lower() == "/list":
        user_list = ", ".join(usernames.values())
        response = f"*** Connected users ({len(usernames)}): {user_list}"
        try:
          client_socket.send(response.encode("utf-8"))
        except:
          break
      else:
        broadcast(f"{username}: {msg_str}", client_socket, clients, usernames)
  except:
    pass
  finally:
    remove_client(client_socket, clients, usernames)


def broadcast(message_str, sender_socket, clients, usernames):
  print(message_str)
  for client in clients:
    if client != sender_socket:
      try:
        client.send(message_str.encode("utf-8"))
      except:
        client.close()
        remove_client(client, clients, usernames)


def remove_client(client_socket, clients, usernames):
  if client_socket in clients:
    username = usernames.get(client_socket, "Unknown")
    clients.remove(client_socket)
    if client_socket in usernames:
      del usernames[client_socket]
    client_socket.close()
    broadcast(f"*** {username} has left the chat. ***", None, clients, usernames)


def run_server():
  host = "0.0.0.0"
  port = 6667

  server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server.bind((host, port))
  server.listen()

  hostname = socket.gethostname()
  local_ip = socket.gethostbyname(hostname)

  print(f"\n[*] Standard IRC Server started on port {port}!")
  print(f"[*] Share this IP address with others: {local_ip}")
  print(
      "[*] Waiting for connections... Press Ctrl+C to stop.\n"
      "--------------------------------------------------"
  )

  clients = []
  usernames = {}

  try:
    while True:
      client_socket, address = server.accept()
      clients.append(client_socket)
      thread = threading.Thread(
          target=handle_client, args=(client_socket, clients, usernames)
      )
      thread.daemon = True
      thread.start()
  except KeyboardInterrupt:
    print("\n[*] Shutting down server...")
    server.close()


# ==========================================
# ANONYMOUS & DISAPPEARING SERVER LOGIC
# ==========================================


def run_anon_server():
  host = "0.0.0.0"
  port = 6668  # Different port for anonymous mode

  server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server.bind((host, port))
  server.listen()

  hostname = socket.gethostname()
  local_ip = socket.gethostbyname(hostname)

  print(f"\n[*] Anonymous Disappearing Server started on port {port}!")
  print(f"[*] Share this IP address with others: {local_ip}")
  print(
      "[*] Waiting for anonymous connections... Press Ctrl+C to stop.\n"
      "--------------------------------------------------"
  )

  clients = []

  def handle_anon_client(client_socket):
    anon_name = f"Anon_{random.randint(1000, 9999)}"
    try:
      # Notify others
      anon_broadcast(
          f"*** {anon_name} entered the shadows. ***", client_socket, clients
      )
      while True:
        message = client_socket.recv(1024)
        if not message:
          break
        msg_str = message.decode("utf-8").strip()
        anon_broadcast(f"{anon_name}: {msg_str}", client_socket, clients)
    except:
        pass
    finally:
      if client_socket in clients:
        clients.remove(client_socket)
      client_socket.close()
      anon_broadcast(
          f"*** {anon_name} vanished from the shadows. ***", None, clients
      )

  def anon_broadcast(message_str, sender_socket, clients_list):
    print(message_str)
    for client in clients_list:
      if client != sender_socket:
        try:
          # Prefix with 'EPHEMERAL|' so clients know to auto-delete it
          client.send(f"EPHEMERAL|{message_str}".encode("utf-8"))
        except:
          client.close()
          if client in clients_list:
            clients_list.remove(client)

  try:
    while True:
      client_socket, address = server.accept()
      clients.append(client_socket)
      thread = threading.Thread(
          target=handle_anon_client, args=(client_socket,)
      )
      thread.daemon = True
      thread.start()
  except KeyboardInterrupt:
    print("\n[*] Shutting down anonymous server...")
    server.close()


# ==========================================
# CLIENT UI (Buffer-Safe & Ephemeral Support)
# ==========================================

if sys.platform == "win32":
  import msvcrt
else:
  import select
  import termios
  import tty


def get_non_blocking_char():
  if sys.platform == "win32":
    if msvcrt.kbhit():
      return msvcrt.getch().decode("utf-8", errors="ignore")
    return None
  else:
    if select.select([sys.stdin], [], [], 0.05)[0]:
      return sys.stdin.read(1)
    return None


class ChatClientUI:

  def __init__(self, client_socket, username, is_ephemeral=False):
    self.client_socket = client_socket
    self.username = username
    self.is_ephemeral = is_ephemeral
    self.current_input = []
    self.running = True
    self.lock = threading.Lock()

  def redraw_line(self):
    prompt = "> "
    typed_text = "".join(self.current_input)
    sys.stdout.write(f"\r\033[K{prompt}{typed_text}")
    sys.stdout.flush()

  def receive_messages(self):
    while self.running:
      try:
        raw_message = self.client_socket.recv(1024).decode("utf-8")
        if not raw_message:
          break

        is_ephemeral_msg = raw_message.startswith("EPHEMERAL|")
        message = (
            raw_message.replace("EPHEMERAL|", "", 1)
            if is_ephemeral_msg
            else raw_message
        )

        with self.lock:
          sys.stdout.write("\r\033[K")
          print(message)
          self.redraw_line()

        # If it's an anonymous/disappearing message, schedule its deletion after 6 seconds
        if is_ephemeral_msg and self.is_ephemeral:
          threading.Thread(
              target=self.expire_message_line, args=(message,), daemon=True
          ).start()

      except:
        break
    self.running = False

  def expire_message_line(self, message_text):
    time.sleep(6)  # Disappear after 6 seconds
    with self.lock:
      # Clear current prompt, move up, clear the message line, and restore prompt
      sys.stdout.write("\r\033[K")  # Clear prompt line
      sys.stdout.write("\033[1A\033[K")  # Move up 1 line and clear message line
      self.redraw_line()

  def start(self):
    old_settings = None
    if sys.platform != "win32":
      fd = sys.stdin.fileno()
      old_settings = termios.tcgetattr(fd)
      tty.setcbreak(fd)

    mode_desc = (
        "ANONYMOUS SHADOW ROOM (Messages disappear after 6s)"
        if self.is_ephemeral
        else f"Connected as **{self.username}**"
    )
    print(
        f"\n[*] {mode_desc}!"
        "\nType your messages and press Enter. Type `/quit` to exit.\n"
        "--------------------------------------------------"
    )
    self.redraw_line()

    recv_thread = threading.Thread(target=self.receive_messages, daemon=True)
    recv_thread.start()

    try:
      while self.running:
        char = get_non_blocking_char()
        if char is None:
          continue

        with self.lock:
          if char in ("\n", "\r"):
            sys.stdout.write("\n")
            msg = "".join(self.current_input).strip()
            self.current_input = []

            if msg:
              if msg.lower() == "/quit":
                self.running = False
                break
              elif msg.lower() == "/help" and not self.is_ephemeral:
                print(
                    "*** Available Commands:\n"
                    "  /list  - Show connected users\n"
                    "  /help  - Show help\n"
                    "  /quit  - Exit chat"
                )
              else:
                try:
                  self.client_socket.send(msg.encode("utf-8"))
                  # If ephemeral, also delete our own sent message from view after 6s to keep it clean
                  if self.is_ephemeral:
                    sent_display = f"{self.username}: {msg}"
                    # Move up past the newline we just printed, clear it, and redraw prompt
                    sys.stdout.write("\033[1A\033[K")
                    self.redraw_line()
                except:
                  print("[!] Failed to send message.")
                  break
            if self.running:
              self.redraw_line()

          elif char in ("\x7f", "\b"):
            if self.current_input:
              self.current_input.pop()
              self.redraw_line()

          elif ord(char) >= 32:
            self.current_input.append(char)
            self.redraw_line()

    finally:
      if sys.platform != "win32" and old_settings:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
      self.client_socket.close()
      print("\n[*] Exited chat.")


def run_client():
  target_ip = input("Enter server IP address (e.g., 192.168.1.15): ").strip()
  port = 6667
  username = input("Choose your chat nickname: ").strip()

  client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
    client.connect((target_ip, port))
  except Exception as e:
    print(f"[!] Could not connect to server: {e}")
    return

  client.send(username.encode("utf-8"))
  ui = ChatClientUI(client, username, is_ephemeral=False)
  ui.start()


def run_anon_client():
  target_ip = input(
      "Enter Anonymous Server IP address (e.g., 192.168.1.15): "
  ).strip()
  port = 6668

  client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
    client.connect((target_ip, port))
  except Exception as e:
    print(f"[!] Could not connect to anonymous server: {e}")
    return

  ui = ChatClientUI(client, "You", is_ephemeral=True)
  ui.start()


# ==========================================
# MAIN ENTRY POINT
# ==========================================

if __name__ == "__main__":
  print("=== Python LAN IRC Chat ===")
  print("1. Start Standard Server (Host)")
  print("2. Join Standard Chat (Client)")
  print("3. Start Anonymous Disappearing Server (Host)")
  print("4. Join Anonymous Disappearing Chat (Client)")
  choice = input("Select mode (1, 2, 3, or 4): ").strip()

  if choice == "1":
    run_server()
  elif choice == "2":
    run_client()
  elif choice == "3":
    run_anon_server()
  elif choice == "4":
    run_anon_client()
  else:
    print("Invalid choice. Please run the script again and select 1, 2, 3, or 4.")