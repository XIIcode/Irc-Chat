import socket
import sys
import threading

# ==========================================
# SERVER LOGIC
# ==========================================


def handle_client(client_socket, clients, usernames):
  try:
    # First message received is the username
    username = client_socket.recv(1024).decode("utf-8")
    usernames[client_socket] = username
    broadcast(f"*** {username} has joined the chat. ***", client_socket, clients, usernames)

    while True:
      message = client_socket.recv(1024)
      if not message:
        break
      msg_str = message.decode("utf-8")
      broadcast(f"{username}: {msg_str}", client_socket, clients, usernames)
  except:
    pass
  finally:
    remove_client(client_socket, clients, usernames)


def broadcast(message_str, sender_socket, clients, usernames):
  print(message_str)  # Print on server console
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
  host = "0.0.0.0"  # Listen on all available network interfaces
  port = 6667  # Standard IRC port

  server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server.bind((host, port))
  server.listen()

  # Find local IP to display to the host
  hostname = socket.gethostname()
  local_ip = socket.gethostbyname(hostname)

  print(f"\n[*] IRC Server successfully started!")
  print(f"[*] Share this IP address with others on your network: {local_ip}")
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
# CLIENT LOGIC
# ==========================================


def receive_messages(client_socket):
  while True:
    try:
      message = client_socket.recv(1024).decode("utf-8")
      if message:
        print(message)
      else:
        break
    except:
      print("\n[!] Disconnected from server.")
      break
  client_socket.close()
  sys.exit()


def run_client():
  target_ip = input(
      "Enter server IP address (e.g., 192.168.1.15): "
  ).strip()
  port = 6667
  username = input("Choose your chat nickname: ").strip()

  client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
    client.connect((target_ip, port))
  except Exception as e:
    print(f"[!] Could not connect to server: {e}")
    return

  # Send username to server
  client.send(username.encode("utf-8"))
  print(
      f"\n[*] Connected to chat as **{username}**!"
      "\nType your messages and press Enter. Type `/quit` to exit.\n"
      "--------------------------------------------------"
  )

  # Start background thread to listen for incoming messages
  recv_thread = threading.Thread(
      target=receive_messages, args=(client,), daemon=True
  )
  recv_thread.start()

  # Main loop for sending messages
  while True:
    try:
      msg = input()
      if msg.lower() == "/quit":
        client.close()
        break
      if msg.strip():
        client.send(msg.encode("utf-8"))
    except (KeyboardInterrupt, EOFError):
      client.close()
      break
  print("\n[*] Exited chat.")


# ==========================================
# MAIN ENTRY POINT
# ==========================================

if __name__ == "__main__":
  print("=== Python LAN IRC Chat ===")
  print("1. Start Server (Host)")
  print("2. Join Chat (Client)")
  choice = input("Select mode (1 or 2): ").strip()

  if choice == "1":
    run_server()
  elif choice == "2":
    run_client()
  else:
    print("Invalid choice. Please run the script again and select 1 or 2.")