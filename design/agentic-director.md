# Continue the first chat with the second chat's answer

Status: LATER. For Agentic Flows with directors. Not for `gpt-oss-120b`.

Cascading chats: the classifier starts a second chat to do the work. Three ways to continue.

1. Accept the limit. A reply to the first chat continues the classifier. It does not continue the second chat.
2. Build a way to continue the redirected chat.
3. Do not continue the second chat. Bring its answer back into the first, and continue the first. The second chat ends when the answer is returned.

The third makes the first chat the director. It reads the answer and the next message and decides what happens next. `gpt-oss-120b` does not do that job. It translates one narrow request into a function call.

Saved 2026-10-30. Investigate when building Agentic Flows with directors.
