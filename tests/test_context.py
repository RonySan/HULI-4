from huli.brain import ContextEngine


def test_context_tracks_turns_and_projects_per_session() -> None:
    context = ContextEngine(max_turns=2)
    context.observe("a", "oi", "smalltalk")
    context.observe("a", "tarefas", "task.list")
    context.observe("a", "hora", "time.query")
    context.set_active_project("a", "Medynx")
    assert [turn.text for turn in context.recent_turns("a", 10)] == ["tarefas", "hora"]
    assert context.snapshot("a").active_project == "Medynx"
    assert context.snapshot("b").active_project is None
