module.exports = {
  apps: [{
    name: "note-discord",
    script: "main.py",
    interpreter: "python3",
    autorestart: true,
    watch: false,
    max_restarts: 5,
    restart_delay: 5000,
    env: {
      PYTHONUNBUFFERED: "1"
    }
  }]
};
