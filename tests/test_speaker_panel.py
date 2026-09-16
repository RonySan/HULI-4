"""Smoke do painel em banco temporário, sem microfone ou conta Google."""
import pytest
from huli.bootstrap import build_runtime
from huli.infrastructure.config import Settings


def test_panel_opens_without_voice_profile_and_keeps_keyboard(tmp_path):
    tk = pytest.importorskip('tkinter')
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip('Tela indisponível')
    root.withdraw()
    from huli.gui import HuliPanel
    runtime = build_runtime(Settings(data_dir=tmp_path, environment='test',
                                     log_level='CRITICAL', desktop_resident_enabled=False,
                                     voice_wake_enabled=False, voice_owner_only=True))
    panel = None
    try:
        panel = HuliPanel(root, runtime)
        root.update_idletasks()
        assert panel.speaker_button['text'] == '🔐 Minha voz'
        assert str(panel.command_entry['state']) == 'normal'
        assert panel.voice.service.speaker_verification_enabled()
        assert not panel.voice.service.speaker_profile_ready()
        assert 'Clique em' in panel.transcript.get('1.0', 'end')
    finally:
        if panel:
            panel.close()
        else:
            runtime.agenda_reminders.stop()
            runtime.timers.shutdown()
            root.destroy()
