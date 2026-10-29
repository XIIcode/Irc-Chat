module.exports = {
  apps: [
    {
      name: "lan-irc-server",
      script: "chat.py",
      args: "server",
      interpreter: "python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "200M",
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
