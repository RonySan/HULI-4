"""Capabilities permitted through the private web/mobile client."""

REMOTE_ALLOWED_INTENTS = frozenset({
    "system.status", "time.query", "date.query", "morning.briefing",
    "agenda.query", "agenda.create", "task.create", "task.list",
    "task.complete", "daily.summary", "smalltalk", "conversation.recap",
    "project.query", "memory.remember", "memory.recall", "memory.list",
    "knowledge.describe", "knowledge.relation", "unknown",
    "spotify.play", "spotify.pause", "spotify.resume", "spotify.next", "spotify.list",
})


def remote_intent_allowed(intent: str) -> bool:
    """Fail closed when new intents are added without a remote security review."""
    return intent in REMOTE_ALLOWED_INTENTS
