import os
import random
import socket
import ssl
import sys
import threading
import time

# ==========================================
# AUTO-CERTIFICATE GENERATOR (Warning-Free)
# ==========================================


def ensure_certificates():
  if not os.path.exists("cert.pem") or not os.path.exists("key.pem"):
    print("[*] Generating SSL certificates for encryption...")
    try:
      from cryptography import x509
      from cryptography.hazmat.primitives import hashes
      from cryptography.hazmat.primitives.asymmetric import rsa
      from cryptography.hazmat.primitives.serialization import (
          Encoding,
          NoEncryption,
          PrivateFormat,
      )
      from cryptography.x509.name import NameAttribute
      from cryptography.x509.oid import NameOID
      import datetime

      private_key = rsa.generate_private_key(
          public_exponent=65537, key_size=2048
      )
      now = datetime.datetime.now(datetime.timezone.utc)
      subject = issuer = x509.Name(
          [x509.NameAttribute(NameOID.COMMON_NAME, "LANChat")]
      )
      cert = (
          x509.CertificateBuilder()
          .subject_name(subject)
          .issuer_name(issuer)
          .public_key(private_key.public_key())
          .serial_number(x509.random_serial_number())
          .not_valid_before(now)
          .not_valid_after(now + datetime.timedelta(days=365))
          .add_extension(
              x509.BasicConstraints(ca=True, path_length=None), critical=True
          )
          .sign(private_key, hashes.SHA256())
      )

      with open("key.pem", "wb") as f:
        f.write(
            private_key.private_bytes(
                Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()
            )
        )

      with open("cert.pem", "wb") as f:
        f.write(cert.public_bytes(Encoding.PEM))

      print("[*] Certificates generated successfully!")
    except ImportError:
      print(
          "\033[91m[!] 'cryptography' module not found.\n"
          "Please run: pip install cryptography\033[0m"
      )
      sys.exit(1)


# ==========================================
# COLOR PALETTE FOR TERMINAL
# ==========================================
COLORS = [
    "\033[91m",  # Bright Red
    "\033[92m",  # Bright Green
    "\033[93m",  # Bright Yellow
    "\033[94m",  # Bright Blue
    "\033[95m",  # Bright Magenta
    "\033[96m",  # Bright Cyan
]
RESET = "\033[0m"

message_history = []
user_colors = {}

# ==========================================
# SECURE STANDARD SERVER LOGIC
# ==========================================


def handle_client(client_socket, clients, usernames):
  try:
    username = client_socket.recv(1024).decode("utf-8").strip()
    usernames[client_socket] = username

    available_colors = [c for c in COLORS if c not in user_colors.values()]
    assigned_color = (
        random.choice(available_colors)
        if available_colors
        else random.choice(COLORS)
    )
    user_colors[client_socket] = assigned_color

    for past_msg in message_history:
      try:
        client_socket.send((past_msg + "\n").encode("utf-8"))
        time.sleep(0.01)
      except:
        break

    broadcast(
        f"\033[90m*** {username} has joined the chat. ***{RESET}",
        client_socket,
        clients,
        usernames,
    )

    while True:
      message = client_socket.recv(1024)
      if not message:
        break
      msg_str = message.decode("utf-8").strip()

      if msg_str.lower() == "/list":
        user_list = ", ".join(usernames.values())
        response = (
            f"\033[93m*** Connected users ({len(usernames)}): {user_list} ***"
            f"{RESET}"
        )
        try:
          client_socket.send((response + "\n").encode("utf-8"))
        except:
          break
      else:
        color = user_colors.get(client_socket, "\033[97m")
        formatted_msg = f"{color}{username}: {msg_str}{RESET}"
        broadcast(formatted_msg, client_socket, clients, usernames)
  except:
    pass
  finally:
    remove_client(client_socket, clients, usernames)


def broadcast(message_str, sender_socket, clients, usernames):
  print(message_str)

  if not "*** " in message_str:
    message_history.append(message_str)
    if len(message_history) > 100:
      message_history.pop(0)

  for client in clients:
    if client != sender_socket:
      try:
        client.send((message_str + "\n").encode("utf-8"))
      except:
        client.close()
        remove_client(client, clients, usernames)


def remove_client(client_socket, clients, usernames):
  if client_socket in clients:
    username = usernames.get(client_socket, "Unknown")
    clients.remove(client_socket)
    if client_socket in usernames:
      del usernames[client_socket]
    if client_socket in user_colors:
      del user_colors[client_socket]
    client_socket.close()
    broadcast(
        f"\033[90m*** {username} has left the chat. ***{RESET}",
        None,
        clients,
        usernames,
    )


def run_server():
  ensure_certificates()
  host = "0.0.0.0"
  port = 6667

  context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
  context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

  server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server.bind((host, port))
  server.listen()
  server.settimeout(1.0)

  hostname = socket.gethostname()
  local_ip = socket.gethostbyname(hostname)

  print(
      f"\n\033[92m[*] SECURE Encrypted IRC Server started on port"
      f" {port}!\033[0m"
  )
  print(
      f"\033[96m[*] Share this IP address with others: {local_ip}\033[0m"
  )
  print(
      "[*] Waiting for encrypted connections... Press Ctrl+C to stop.\n"
      "--------------------------------------------------"
  )

  clients = []
  usernames = {}

  try:
    while True:
      try:
        raw_socket, address = server.accept()
      except socket.timeout:
        continue

      client_socket = context.wrap_socket(raw_socket, server_side=True)
      clients.append(client_socket)
      thread = threading.Thread(
          target=handle_client, args=(client_socket, clients, usernames)
      )
      thread.daemon = True
      thread.start()
  except KeyboardInterrupt:
    print("\n\033[91m[*] Shutting down server...\033[0m")
    server.close()


# ==========================================
# SECURE ANONYMOUS SERVER LOGIC
# ==========================================


def run_anon_server():
  ensure_certificates()
  host = "0.0.0.0"
  port = 6668

  context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
  context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

  server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server.bind((host, port))
  server.listen()
  server.settimeout(1.0)

  hostname = socket.gethostname()
  local_ip = socket.gethostbyname(hostname)

  print(
      f"\n\033[95m[*] SECURE Anonymous Disappearing Server started on port"
      f" {port}!\033[0m"
  )
  print(
      f"\033[96m[*] Share this IP address with others: {local_ip}\033[0m"
  )
  print(
      "[*] Waiting for secure anonymous connections... Press Ctrl+C to"
      " stop.\n--------------------------------------------------"
  )

  clients = []

  def handle_anon_client(client_socket):
    anon_name = f"Anon_{random.randint(1000, 9999)}"
    anon_color = random.choice(COLORS)
    try:
      anon_broadcast(
          f"\033[90m*** {anon_name} entered the shadows. ***{RESET}",
          client_socket,
          clients,
      )
      while True:
        message = client_socket.recv(1024)
        if not message:
          break
        msg_str = message.decode("utf-8").strip()
        anon_broadcast(
            f"{anon_color}{anon_name}: {msg_str}{RESET}", client_socket, clients
        )
    except:
      pass
    finally:
      if client_socket in clients:
        clients.remove(client_socket)
      client_socket.close()
      anon_broadcast(
          f"\033[90m*** {anon_name} vanished from the shadows. ***{RESET}",
          None,
          clients,
      )

  def anon_broadcast(message_str, sender_socket, clients_list):
    print(message_str)
    for client in clients_list:
      if client != sender_socket:
        try:
          client.send(f"EPHEMERAL|{message_str}\n".encode("utf-8"))
        except:
          client.close()
          if client in clients_list:
            clients_list.remove(client)

  try:
    while True:
      try:
        raw_socket, address = server.accept()
      except socket.timeout:
        continue

      client_socket = context.wrap_socket(raw_socket, server_side=True)
      clients.append(client_socket)
      thread = threading.Thread(
          target=handle_anon_client, args=(client_socket,)
      )
      thread.daemon = True
      thread.start()
  except KeyboardInterrupt:
    print("\n\033[91m[*] Shutting down anonymous server...\033[0m")
    server.close()


# ==========================================
# CLIENT UI
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
    prompt = "\033[92m> \033[0m"
    typed_text = "".join(self.current_input)
    sys.stdout.write(f"\r\033[K{prompt}{typed_text}")
    sys.stdout.flush()

  def receive_messages(self):
    buffer = ""
    while self.running:
      try:
        data = self.client_socket.recv(1024).decode("utf-8")
        if not data:
          break

        buffer += data
        while "\n" in buffer:
          line, buffer = buffer.split("\n", 1)
          line = line.strip("\r")
          if not line:
            continue

          is_ephemeral_msg = line.startswith("EPHEMERAL|")
          message = (
              line.replace("EPHEMERAL|", "", 1) if is_ephemeral_msg else line
          )

          with self.lock:
            sys.stdout.write("\r\033[K")
            print(message)
            self.redraw_line()

          if is_ephemeral_msg and self.is_ephemeral:
            threading.Thread(
                target=self.expire_message_line, args=(message,), daemon=True
            ).start()

      except:
        break
    self.running = False

  def expire_message_line(self, message_text):
    time.sleep(6)
    with self.lock:
      sys.stdout.write("\r\033[K")
      sys.stdout.write("\033[1A\033[K")
      self.redraw_line()

  def start(self):
    old_settings = None
    if sys.platform != "win32":
      fd = sys.stdin.fileno()
      old_settings = termios.tcgetattr(fd)
      tty.setcbreak(fd)

    mode_desc = (
        "\033[95mSECURE ANONYMOUS ROOM (Messages disappear after 6s)\033[0m"
        if self.is_ephemeral
        else f"Connected securely as \033[93m{self.username}\033[0m"
    )
    print(
        f"\n[*] {mode_desc}!"
        "\nType your messages and press Enter. Type \033[91m`/quit`\033[0m to"
        " exit.\n--------------------------------------------------"
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
              elif msg.lower() == "/clear":
                # Clear terminal screen and redraw header & prompt
                sys.stdout.write("\033[2J\033[H")
                print(
                    f"\n[*] Connected securely as \033[93m{self.username}\033[0m"
                    "\nType your messages and press Enter. Type"
                    " \033[91m`/quit`\033[0m to"
                    " exit.\n--------------------------------------------------"
                )
              elif msg.lower() == "/help" and not self.is_ephemeral:
                print(
                    "\033[93m*** Available Commands:\n"
                    "  /list  - Show connected users\n"
                    "  /clear - Clear terminal screen\n"
                    "  /help  - Show help\n"
                    "  /quit  - Exit chat\033[0m"
                )
              else:
                try:
                  self.client_socket.send(msg.encode("utf-8"))
                  if self.is_ephemeral:
                    sys.stdout.write("\033[1A\033[K")
                    self.redraw_line()
                except:
                  print("\033[91m[!] Failed to send message.\033[0m")
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
      print("\n\033[91m[*] Exited chat.\033[0m")


def run_client():
  target_ip = input("Enter server IP address (e.g., 192.168.1.15): ").strip()
  port = 6667
  username = input("Choose your chat nickname: ").strip()

  context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
  context.check_hostname = False
  context.verify_mode = ssl.CERT_NONE

  normal_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  client = context.wrap_socket(normal_socket)

  try:
    client.connect((target_ip, port))
  except Exception as e:
    print(f"\033[91m[!] Could not connect to secure server: {e}\033[0m")
    return

  client.send(username.encode("utf-8"))
  ui = ChatClientUI(client, username, is_ephemeral=False)
  ui.start()


def run_anon_client():
  target_ip = input(
      "Enter Anonymous Server IP address (e.g., 192.168.1.15): "
  ).strip()
  port = 6668

  context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
  context.check_hostname = False
  context.verify_mode = ssl.CERT_NONE

  normal_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  client = context.wrap_socket(normal_socket)

  try:
    client.connect((target_ip, port))
  except Exception as e:
    print(f"\033[91m[!] Could not connect to secure anonymous server: {e}\033[0m")
    return

  ui = ChatClientUI(client, "You", is_ephemeral=True)
  ui.start()


# ==========================================
# MAIN ENTRY POINT (PM2 / CLI SUPPORT)
# ==========================================

if __name__ == "__main__":
  if len(sys.argv) > 1:
    mode = sys.argv[1].lower()
    if mode == "server":
      run_server()
    elif mode == "anon":
      run_anon_server()
    else:
      print("Unknown mode. Use 'server' or 'anon'.")
  else:
    print("\033[96m=== Secure Python LAN IRC Chat ==-\033[0m")
    print("1. Start Secure Standard Server (Host)")
    print("2. Join Secure Standard Chat (Client)")
    print("3. Start Secure Anonymous Disappearing Server (Host)")
    print("4. Join Secure Anonymous Disappearing Chat (Client)")
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
      print(
          "\033[91mInvalid choice. Please run the script again and select 1, 2,"
          " 3, or 4.\033[0m"
      )