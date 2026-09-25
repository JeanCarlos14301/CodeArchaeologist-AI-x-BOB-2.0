# Security Guidelines for Watsonx Hackathon

Adopted from the official [IBM Hackathon GitHub project template](https://github.com/watsonxhackathon/ibm-hackathon-template).
These rules apply on top of, and never override, [AGENTS.md](AGENTS.md).

## 🔒 Credential Management

### ✅ DO:

- ✅ Use environment variables for ALL credentials
- ✅ Copy `.env.example` to `.env` and add your credentials there
- ✅ Keep `.env` in `.gitignore` (already configured)
- ✅ Use `os.getenv('VARIABLE_NAME')` (Python) or `process.env.VARIABLE_NAME` (Node) in code
- ✅ Review your commits before pushing (`git diff`)
- ✅ Use placeholders when asking AI assistants (Bob included) for help

### ❌ DON'T:

- ❌ Never hardcode API keys in your code
- ❌ Never commit `.env` files
- ❌ Never share credentials in code comments
- ❌ Never commit files with "credential", "secret", or "password" in the name
- ❌ Never remove patterns from `.gitignore` or `.bobignore`
- ❌ Never paste credentials in AI assistant prompts

## 🤖 Using AI Assistants Safely (Bob, Copilot, etc.)

### The Risk

AI assistants log your prompts and code in session history files. If you share credentials with them, those credentials may be logged.

### Safe Practices:

```
❌ BAD:  "Here's my API key: abc123xyz, help me use it"
✅ GOOD: "Help me use environment variables for my API key"

❌ BAD:  "Read my .env file and help me debug"
✅ GOOD: "Help me structure my .env file (I'll add credentials myself)"

❌ BAD:  api_key = "abc123xyz"
✅ GOOD: api_key = os.getenv('IBM_CLOUD_API_KEY')
```

### Protection:

- `.bobignore` prevents Bob from logging credential patterns.
- `.gitignore` prevents session files from being committed.
- But **you** must still not share credentials in prompts.

## 🚨 What Happens if You Expose Credentials?

If you accidentally commit credentials:

1. Your IBM Cloud account will be suspended immediately.
2. You must remove the credential from repository history.
3. You must rotate/revoke the exposed credential.
4. Your account will be restored after verification.

## 📝 How to Use Environment Variables

### Python (this project's backend)

```python
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("IBM_CLOUD_API_KEY")
```

### Node.js / JavaScript (this project's frontend build tooling)

```javascript
require("dotenv").config();
const apiKey = process.env.IBM_CLOUD_API_KEY;
```

## 📸 IBM Bob Session Screenshots

Each team member must export and commit screenshots of their own IBM Bob task session
summaries to `bob-sessions/<name>/` (see [bob-sessions/README.md](bob-sessions/README.md)).
Screenshots must **never** contain a visible API key, token, or credential — crop or blur
any such field before committing. `bob-sessions/` is tracked in git and is **not** ignored.

## 🔍 Before You Commit Checklist

- [ ] No hardcoded credentials in code
- [ ] `.env` file is NOT staged for commit
- [ ] No files with credentials in their name
- [ ] Reviewed `git diff` for sensitive data
- [ ] All credentials are in environment variables
- [ ] No credentials shared with AI assistants
- [ ] No credentials visible in any `bob-sessions/` screenshot

## 🆘 Need Help?

Contact hackathon support through the mentor channel.

## 📚 Additional Resources

- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [IBM Cloud Security](https://cloud.ibm.com/docs/account?topic=account-security)
- [Environment Variables Guide](https://12factor.net/config)
