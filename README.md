# DropMail Python Wrapper

**Python wrapper for [DropMail](https://dropmail.me) temporary email service with [Mirror Support](https://mirror2.dropmail.info/).**
**Please scroll down to see everything, you may miss a lot of important things!**

## Installation

```bash
pip install dropmail
```

### Simple Usage

```bash
from dropmail import dropmail

# Get a temporary email
email, check = dropmail()
print(f"{email}")

# Check for messages
messages = check()
for msg in messages:
    print(f"From: {msg['fromAddr']}")
    print(f"Subject: {msg['headerSubject']}")
    print(f"Message: {msg['text']}")
```

### Wait for message

```bash
email, check = dropmail(wait=True, timeout=300)
```

# Advanced Usage

```bash
from dropmail import dropmailplus

# Create client
client = dropmailplus()

# Create new email session
session = client.create()
print(f"Email: {session['email']}")
print(f"Session ID: {session['session_id']}")
print(f"Expires at: {session['expires_at']}")

# Wait for message
message = client.wait_for_message(session['session_id'], timeout=120)
if message:
    print(f"Received: {message['headerSubject']}")

# Get all messages
messages = client.get_messages(session['session_id'])

# Get all active sessions
sessions = client.get_all_sessions()
```

## API Reference (SYNC)
```bash
dropmail(wait=False, timeout=300, domain=None, blocking=True)
```
Way to create temporary email.
Parameters:
- wait (bool): Wait for first message if True
- domain (string): Example "dropmail.me"
- blocking (bool): Blocking flow until get mail 
Returns:
- Tuple of (email_address, check_function)

### DropMail Class
```bash
dropmailplus(token=None, timeout=30)
```
Initialize client with optional token if "**None**" = autogenerate token.

```bash
create(domain=None)
```
Create new email with session id. 
Returns dict with session_id, email, emails (all), expires_at.

```bash
restore_session(session_id)
```
Restore session (mail) by id

```bash
get_messages(session_id, only_new=False)
```
- only_new (bool): Unreaded messages only.
Get all messages for session.

```bash
wait_for_message(session_id, timeout=300, poll_interval=2, filter_func=None, only_new=True)
```
- filter_func (func) - filter function (example lambda msg: msg['fromAddr'] == 'test@dropmail.me')
Wait for first message to arrive.

```bash
wait_for_messages(session_id, count=1, timeout=300, poll_interval=2, filter_func=None)
```
Waiting for multiple messages before returning them.

```bash
filter_messages(messages, from_addr=None, subject_contains=None, text_contains=None)
```

```bash
get_all_sessions()
```
Get all active sessions for current token.

## API Reference (ASYNC)

```bash
async_dropmail(wait=False, timeout=300, domain=None)
async_dropmailplus(token=None, timeout=30)
```

## Message structure (IMPORTANT)

- **fromAddr** - from address
- **toAddr** - to address
- **headerSubject** - theme of mail
- **text** - text from the mail
- **html** - HTML version
- **downloadUrl** - obvious
- **rawSize** - size in bytes
- **receivedAt** - recived time

## Available domains
- **dropmail.me**
- **10mail.org**
- **yomail.info**
- **emltmp.com**
- **emlpro.com**
- **emlhub.com**
- **freeml.net**
- **spymail.one**
- **mailpwr.com**
- **mimimail.me**
- **10mail.xyz**

### License
*MIT*

## Contributing
*Pull requests are welcome! Please feel free to submit a Pull Request.*
