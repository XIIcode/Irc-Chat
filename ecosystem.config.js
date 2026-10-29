module.exports = {
  apps: [
    {
      name: "lan-irc-server",
      script: "chat.py",
      args: "server", // change to anon to start in anon mode.
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
