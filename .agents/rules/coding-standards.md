# Project Coding Standards & Guidelines

1. **Python / Rasa**:
   - Keep actions inside `actions/` modular and well-documented.
   - Run validation before model training.
   - Use `/home/ubuntu/rasa-env/bin/python` for virtualenv executions.

2. **Mandatory Bot Restart After Updates**:
   - Har code, model, action, config, ya skill update ke baad dono Rasa services ko proactively restart karna zaroori hai:
     `sudo systemctl restart rasa-actions.service && sudo systemctl restart rasa-bot.service`
   - Restart ke baad `/version` endpoint aur test chat verify karein.

3. **Security**:
   - Never commit sensitive keys, `.env` files, or production credentials to Git.
   - Ensure external endpoints use proper CORS and authentication where required.

4. **Web & UI**:
   - Clean, modern design with vanilla CSS or Tailwind (when specified).
   - Fully responsive on mobile and desktop devices.
