---
name: whatsapp
description: "Send or read WhatsApp messages. Use when the user wants to message a contact or group, e.g. '/whatsapp Andrei hey, check the new data'."
user_invocable: true
---

# WhatsApp

Send and read WhatsApp messages via the whatsapp-mcp bridge.

## Before any WhatsApp tool call

Check if the bridge is running:

```bash
curl -sf http://localhost:8080/api/send 2>/dev/null
```

If no response, start it:

```bash
nohup ~/whatsapp-mcp/whatsapp-bridge/bridge > /tmp/whatsapp-bridge.log 2>&1 &
sleep 8  # wait for connection + history sync
```

If the bridge fails with a QR code auth error, tell the user to run:
```
! cd ~/whatsapp-mcp/whatsapp-bridge && ./bridge
```
and scan the QR code with their phone (WhatsApp → Linked Devices → Link a Device). Auth lasts ~20 days.

## Parsing the request

The user may say things like:
- `/whatsapp Andrei hey, the MG data is ready`
- `/whatsapp "Laborjust Sigstad Lambais" meeting tomorrow at 3pm`
- `send a whatsapp to Frida saying hi`
- `check whatsapp messages from Andrei`

Extract:
1. **Who** — contact name or group name
2. **Message** — the text to send (if sending)
3. **Action** — send message, read messages, or search contacts

## Sending a message

1. Use `mcp__whatsapp__search_contacts` to find the recipient by name
2. For groups, use `mcp__whatsapp__list_chats` to find the group JID
3. Use `mcp__whatsapp__send_message` with the phone number or JID

## Reading messages

- Use `mcp__whatsapp__list_messages` to fetch recent messages
- Use `mcp__whatsapp__get_direct_chat_by_contact` for a specific contact's chat

## Project WhatsApp groups

Some projects have associated WhatsApp groups:
- **serasa** (projects/serasa): "SERASA Courts Project"
- **connect** (projects/connect): "LaborJust henrik lambais"
- **procure** (projects/procure): "Corruption Red Flags"
- **audit** (projects/audit): "Legal Effects of Audits"
- **electoral-justice** (projects/electoral-justice): "Electoral justice"
- **segredo** (projects/segredo): Andrei Leite (direct chat)

## Before sending

Show the user the recipient and message, and ask for confirmation before sending — unless the user's request is unambiguous (explicit recipient + explicit message text).

## Gotchas

- If a contact is not found, try partial name matches or ask the user for the phone number.
- Group JIDs end in `@g.us`, individual contacts end in `@s.whatsapp.net`.
- Phone numbers need country code without + or spaces (e.g., "4748142870" for Norway).
- The bridge must have seen a chat to list it — if a group doesn't show up, ask the user to send a message there from their phone first.
