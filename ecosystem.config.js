module.exports = {
  apps: [
    {
      name: "lan-irc-server",
      script: "python",
      args: "irc_chat.py server", // change to "irc_chat.py anon" to run anon server.
      interpreter: "",
      autorestart: true,
      watch: false,
      max_memory_restart: "200M",
      env: {
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};