# Explicit long-term memory

Submit each command with END on a separate line.

- `REMEMBER project_name = JeshlaAutoAI`: save a fact; repeat the same key to update.
- `SHOW MEMORY`: show current stored facts.
- `FORGET project_name`: delete that fact permanently from long-term memory.

Keys are case-sensitive, 1-64 letters/digits/underscore/dot/hyphen. Facts can have up to 2000 characters. Seed JSON is imported once per user/namespace. Deleted seeds are not reinserted. Facts are user assertions, not verified source evidence or action approvals.

No model calls are required for these commands. Normal model answers receive stored memory context, which may be sent to the selected hosted provider. Do not store credentials. FORGET removes a database fact, not previous conversation/checkpoint history or provider records. Chat still retains prior messages, so a fact may remain in recent conversation context.
