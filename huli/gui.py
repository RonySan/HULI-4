"""Painel local da Huli com teclado, escuta pontual e palavra de ativação."""

from __future__ import annotations

from dataclasses import dataclass, field
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from uuid import uuid4

from huli import __app_name__, __version__
from huli.bootstrap import HuliRuntime, build_runtime
from huli.brain.normalization import normalize_text
from huli.core import InvalidKernelInput
from huli.security import AuthenticationError, JournalVaultError
from huli.security.privacy import redact_private_text
from huli.voice import (
    VoiceCancelledError,
    VoiceCommand,
    VoiceError,
    VoiceService,
    VoiceSession,
    VoiceTimeoutError,
    WakeEventKind,
    WakeAliasStore,
    WakeWordListener,
    parse_voice_command,
    parse_wake_control,
    select_repeated_aliases,
)


_WAKE_WRITE_INTENTS = frozenset(
    {
        "agenda.create",
        "agenda.cancel",
        "task.create",
        "task.complete",
        "project.set",
        "project.note",
        "memory.remember",
        "memory.forget",
    }
)


@dataclass(frozen=True, slots=True)
class PanelSession:
    username: str
    role: str
    token: str | None = None
    session_id: str = field(default_factory=lambda: f"gui-{uuid4().hex}")

    @property
    def is_guest(self) -> bool:
        return self.role == "guest"


def _wake_requires_confirmation(intent: str) -> bool:
    return intent in _WAKE_WRITE_INTENTS or intent.startswith("journal.")


class HuliPanel:
    """Interface gráfica que mantém todo comando no Kernel autenticado."""

    def __init__(self, root: tk.Tk, runtime: HuliRuntime | None = None) -> None:
        self.root = root
        self.runtime = runtime or build_runtime()
        settings = self.runtime.settings
        service = VoiceService.local_default(
            language=settings.voice_language,
            input_timeout=settings.voice_input_timeout,
            rate=settings.voice_rate,
            volume=settings.voice_volume,
            input_provider=settings.voice_input_provider,
            model_path=settings.voice_model_path,
            input_device=settings.voice_input_device,
        )
        self.voice = VoiceSession(service=service, auto_speak=settings.voice_auto_speak)
        self.alias_store = WakeAliasStore(
            settings.data_dir / "voice_wake_aliases.json"
        )
        self.wake_aliases = self.alias_store.load()
        self.session: PanelSession | None = None
        self.wake: WakeWordListener | None = None
        self.listening = False
        self.calibrating = False
        self._calibration_cancel = threading.Event()
        self._wake_was_enabled = False
        self.pending_wake_command: tuple[str, float] | None = None
        self._closed = False

        root.title(f"{__app_name__} {__version__} — Painel local")
        root.geometry("920x650")
        root.minsize(720, 500)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._show_login()
        self.root.after(60, self._poll_wake)

    def _clear(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

    def _show_login(self) -> None:
        self._clear()
        frame = ttk.Frame(self.root, padding=36)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="H.U.L.I.", font=("Segoe UI", 25, "bold")).pack(
            pady=(60, 8)
        )
        ttk.Label(
            frame,
            text="Painel local com voz e ativação contínua",
        ).pack(pady=(0, 28))

        form = ttk.Frame(frame)
        form.pack()
        ttk.Label(form, text="Usuário").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Label(form, text="Senha").grid(row=1, column=0, sticky="w", pady=6)
        self.username_entry = ttk.Entry(form, width=34)
        self.password_entry = ttk.Entry(form, width=34, show="•")
        self.username_entry.grid(row=0, column=1, padx=10, pady=6)
        self.password_entry.grid(row=1, column=1, padx=10, pady=6)

        buttons = ttk.Frame(frame)
        buttons.pack(pady=22)
        ttk.Button(buttons, text="Entrar", command=self.login).pack(side="left", padx=5)
        ttk.Button(buttons, text="Entrar como visitante", command=self.login_guest).pack(
            side="left", padx=5
        )
        ttk.Label(
            frame,
            text="O áudio é processado localmente e não é salvo.",
            foreground="#555555",
        ).pack(pady=8)
        self.password_entry.bind("<Return>", lambda _event: self.login())
        self.username_entry.focus_set()

    def login(self) -> None:
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        known = self.runtime.auth.find_user(username)
        if known is None:
            messagebox.showerror("Acesso", "Usuário não reconhecido.")
            return
        try:
            user, token = self.runtime.auth.authenticate(known.username, password)
        except JournalVaultError as exc:
            messagebox.showerror("Cofre privado", str(exc))
            return
        except (AuthenticationError, ValueError):
            messagebox.showerror("Acesso", "Usuário ou senha inválidos.")
            self.password_entry.delete(0, "end")
            return
        self.session = PanelSession(user.username, "owner", token)
        self._show_main()

    def login_guest(self) -> None:
        self.session = PanelSession("Visitante", "guest")
        self._show_main()

    def _show_main(self) -> None:
        self._clear()
        session = self._require_session()

        top = ttk.Frame(self.root, padding=(12, 10))
        top.pack(fill="x")
        ttk.Label(
            top,
            text=f"Sessão: {session.username} ({'proprietário' if not session.is_guest else 'visitante'})",
        ).pack(side="left")
        self.status_var = tk.StringVar(value="Escuta contínua desligada")
        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=24)
        ttk.Button(top, text="Sair da sessão", command=self.logout).pack(side="right")

        self.transcript = scrolledtext.ScrolledText(
            self.root,
            state="disabled",
            wrap="word",
            font=("Segoe UI", 11),
            padx=12,
            pady=12,
        )
        self.transcript.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        controls = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        controls.pack(fill="x")
        self.command_entry = ttk.Entry(controls)
        self.command_entry.pack(side="left", fill="x", expand=True)
        self.listen_button = ttk.Button(
            controls,
            text="🎤 Ouvir agora",
            command=self.listen_once,
        )
        self.listen_button.pack(side="left", padx=(8, 0))
        self.wake_button = ttk.Button(
            controls,
            text="🎙 Escuta contínua: desligada",
            command=self.toggle_wake,
        )
        self.wake_button.pack(side="left", padx=(8, 0))
        self.calibrate_button = ttk.Button(
            controls,
            text="🎯 Calibrar nome",
            command=self.start_calibration,
            state="disabled" if session.is_guest else "normal",
        )
        self.calibrate_button.pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Enviar", command=self.send).pack(side="left", padx=(8, 0))

        ttk.Label(
            self.root,
            text=(
                "Diga “Huli” (como rú-li), espere ‘Estou ouvindo’ e fale o comando. "
                "Se necessário, use “Calibrar nome”. "
                "O teclado tem prioridade e ações que alteram dados pedem confirmação."
            ),
            foreground="#555555",
        ).pack(fill="x", padx=14, pady=(0, 10))

        self.command_entry.bind("<Return>", lambda _event: self.send())
        self.command_entry.bind("<KeyPress>", self._typing_started)
        self.command_entry.bind("<KeyRelease>", self._typing_changed)
        self.command_entry.focus_set()
        self._append(
            "Huli",
            "Sessão iniciada. Use o teclado, ‘Ouvir agora’ ou ligue a escuta contínua.",
        )
        if (
            not session.is_guest
            and self.runtime.settings.voice_wake_enabled
        ):
            self.root.after(250, self._start_configured_wake)

    def _start_configured_wake(self) -> None:
        if self.session is None or self.session.is_guest or self._closed:
            return
        self.set_wake(True)

    def _require_session(self) -> PanelSession:
        if self.session is None:
            raise RuntimeError("Sessão local ausente.")
        return self.session

    def _metadata(self) -> dict[str, object]:
        session = self._require_session()
        return {
            "session_id": session.session_id,
            "username": session.username,
            "role": session.role,
        }

    def _authorized(self, text: str) -> bool:
        session = self._require_session()
        if session.role == "owner":
            try:
                user = self.runtime.auth.validate_token(session.token or "")
            except AuthenticationError:
                return False
            return user.username.casefold() == session.username.casefold()
        intent = self.runtime.intents.classify(text).intent.value
        return self.runtime.security.guest_can_execute(text, intent)

    def _append(self, who: str, text: str) -> None:
        if not hasattr(self, "transcript"):
            return
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{who}: {text}\n\n")
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def _safe_after(self, callback, *args) -> None:
        if self._closed:
            return
        try:
            self.root.after(0, callback, *args)
        except tk.TclError:
            return

    def _typing_started(self, _event=None) -> None:
        if self.wake:
            self.wake.set_typing(True)
            self.status_var.set("Escuta pausada enquanto você digita")

    def _typing_changed(self, _event=None) -> None:
        if self.wake and not self.command_entry.get():
            self.wake.set_typing(False)
            if self.wake.enabled:
                self.status_var.set("Escuta contínua ligada — diga “Huli”")

    def send(self) -> None:
        text = self.command_entry.get().strip()
        if not text:
            return
        self.command_entry.delete(0, "end")
        if self.wake:
            self.wake.pause()
            self.wake.set_typing(False)
        self._append("Você", text)
        self._execute(text, from_wake=False)
        self.command_entry.focus_set()

    def _execute(self, text: str, *, from_wake: bool) -> None:
        resume = bool(self.wake and self.wake.enabled)
        try:
            if normalize_text(text) in {"sair", "exit", "quit"}:
                self.logout()
                return

            if not from_wake and normalize_text(text) == "confirmar voz":
                if self.pending_wake_command and time.monotonic() <= self.pending_wake_command[1]:
                    text = self.pending_wake_command[0]
                    self.pending_wake_command = None
                    self._append("Huli", "Comando de voz confirmado pelo teclado.")
                else:
                    self.pending_wake_command = None
                    self._append("Huli", "Não há comando de voz aguardando confirmação.")
                    return
            elif not from_wake:
                self.pending_wake_command = None

            wake_control = parse_wake_control(text)
            if wake_control is not None:
                self.set_wake(wake_control)
                return

            voice_command = parse_voice_command(text)
            if voice_command is VoiceCommand.LISTEN:
                # A conclusão da captura é responsável por retomar a ativação.
                resume = False
                self.listen_once()
                return
            if voice_command is VoiceCommand.STATUS:
                activation = "ligada" if self.wake and self.wake.enabled else "desligada"
                self._append("Huli", f"{self.voice.status_text()} Ativação: {activation}.")
                return
            if voice_command is VoiceCommand.ENABLE:
                if not self.voice.service.capabilities().output_available:
                    self._append("Huli", self.voice.status_text())
                else:
                    self.voice.auto_speak = True
                    self._append("Huli", "Respostas por voz ativadas.")
                    self._speak("Respostas por voz ativadas.")
                return
            if voice_command is VoiceCommand.DISABLE:
                self.voice.auto_speak = False
                self._append("Huli", "Respostas por voz desativadas.")
                return
            if voice_command is VoiceCommand.CONTINUOUS:
                self.set_wake(True)
                return
            if voice_command is VoiceCommand.STOP:
                self.set_wake(False)
                return

            intent = self.runtime.intents.classify(text).intent.value
            if from_wake and _wake_requires_confirmation(intent):
                self.pending_wake_command = (text, time.monotonic() + 30)
                self._append(
                    "Huli",
                    "Esse comando altera dados. Digite “confirmar voz” nos próximos 30 segundos.",
                )
                return
            if not self._authorized(text):
                session = self._require_session()
                message = (
                    "Sua sessão expirou. Entre novamente."
                    if not session.is_guest
                    else "Essa ação exige acesso do proprietário."
                )
                self._append("Huli", message)
                return

            self.runtime.security.validate_input(text)
            response = self.runtime.kernel.process(text, metadata=self._metadata())
            self._append("Huli", response.text)
            if self.voice.can_speak_response(intent) and response.handled_by != "journal":
                self._speak(response.text)
        except (InvalidKernelInput, ValueError) as exc:
            self._append("Huli", str(exc))
        finally:
            if resume and self.wake and self.wake.enabled:
                self.wake.resume()
                if hasattr(self, "status_var"):
                    self.status_var.set("Escuta contínua ligada — diga “Huli”")

    def _speak(self, text: str) -> None:
        try:
            self.voice.service.speak(text)
        except VoiceError as exc:
            self.voice.auto_speak = False
            self._append("Sistema", f"A fala foi desativada: {exc}")

    def listen_once(self) -> None:
        if self.listening or self.calibrating:
            return
        self.listening = True
        if self.wake:
            self.wake.pause()
        self.listen_button.configure(state="disabled", text="Ouvindo...")
        self.status_var.set("Ouvindo uma frase...")
        self._append("Huli", "Estou ouvindo...")
        threading.Thread(target=self._listen_worker, daemon=True).start()

    def _listen_worker(self) -> None:
        try:
            self.voice.service.prepare_input()
            result: tuple[str, str] = ("ok", self.voice.service.listen_once())
        except VoiceTimeoutError as exc:
            result = ("error", str(exc))
        except VoiceError as exc:
            result = ("error", f"Voz indisponível: {exc}")
        self.root.after(0, self._finish_listen, result)

    def _finish_listen(self, result: tuple[str, str]) -> None:
        self.listening = False
        self.listen_button.configure(state="normal", text="🎤 Ouvir agora")
        kind, text = result
        if kind == "ok":
            self._append("Você [voz]", redact_private_text(text))
            self._execute(text, from_wake=False)
        else:
            self._append("Huli", text)
            if self.wake and self.wake.enabled:
                self.wake.resume()
        self.status_var.set(
            "Escuta contínua ligada — diga “Huli”"
            if self.wake and self.wake.enabled
            else "Escuta contínua desligada"
        )

    def toggle_wake(self) -> None:
        self.set_wake(not bool(self.wake and self.wake.enabled))

    def set_wake(self, enabled: bool) -> None:
        if self.calibrating:
            self._append("Sistema", "Conclua a calibração do nome antes de alterar a escuta.")
            return
        if not enabled:
            if self.wake:
                self.wake.disable()
            self.wake_button.configure(text="🎙 Escuta contínua: desligada")
            self.listen_button.configure(state="normal")
            self.status_var.set("Escuta contínua desligada")
            self._append("Sistema", "Escuta contínua desligada. O teclado continua disponível.")
            return

        try:
            if self.wake is None:
                settings = self.runtime.settings
                self.wake = WakeWordListener(
                    self.voice.service,
                    cycle_timeout=settings.voice_wake_cycle_timeout,
                    command_timeout=settings.voice_input_timeout,
                    feedback=True,
                    aliases=self.wake_aliases,
                )
                self.wake.start()
            else:
                self.wake.enable()
                self.wake.resume()
        except VoiceError as exc:
            if self.wake:
                self.wake.stop()
            self.wake = None
            self._append("Sistema", f"Ativação por voz indisponível: {exc}")
            self.status_var.set("Falha ao iniciar escuta contínua")
            return

        capabilities = self.voice.service.capabilities()
        self.voice.auto_speak = capabilities.output_available
        self.wake_button.configure(text="🎙 Escuta contínua: ligada")
        self.listen_button.configure(state="disabled")
        self.status_var.set("Escuta contínua ligada — diga “Huli”")
        self._append(
            "Sistema",
            "Escuta contínua ligada. Diga “Huli” e o comando; você também pode digitar normalmente.",
        )

    def start_calibration(self) -> None:
        session = self._require_session()
        if session.is_guest:
            messagebox.showinfo(
                "Calibrar nome",
                "A calibração exige a sessão do proprietário.",
            )
            return
        if self.calibrating or self.listening:
            return
        messagebox.showinfo(
            "Calibrar nome",
            "Você falará somente “Huli” cinco vezes. O detector compara os sons "
            "de Huli/Ruli e não aprende palavras como link, olhe ou ruim.\n\n"
            "Observe a mensagem no topo e diga o nome uma vez a cada pedido. "
            "O áudio não será salvo.",
        )
        self.calibrating = True
        self._calibration_cancel = threading.Event()
        self._wake_was_enabled = bool(self.wake and self.wake.enabled)
        if self.wake:
            self.wake.pause()
        self.listen_button.configure(state="disabled")
        self.wake_button.configure(state="disabled")
        self.calibrate_button.configure(state="disabled", text="Calibrando 0/5...")
        self._append(
            "Sistema",
            "Calibração iniciada. Fale somente o nome Huli em cada amostra.",
        )
        threading.Thread(
            target=self._calibration_worker,
            daemon=True,
            name="huli-name-calibration",
        ).start()

    def _calibration_worker(self) -> None:
        samples: list[str] = []
        try:
            self.voice.service.prepare_input()
            for index in range(1, 6):
                if self._calibration_cancel.is_set():
                    return
                self._safe_after(self._show_calibration_prepare, index)
                time.sleep(0.7)
                self._safe_after(self._show_calibration_prompt, index)
                time.sleep(0.1)
                try:
                    heard = self.voice.service.listen_calibration_once(
                        timeout=6,
                        cancel_event=self._calibration_cancel,
                    )
                except VoiceTimeoutError:
                    self._safe_after(self._show_calibration_timeout, index)
                    continue
                if self._calibration_cancel.is_set():
                    return
                samples.append(heard)
                self._safe_after(self._show_calibration_sample, index, heard)
                time.sleep(0.5)
            aliases = select_repeated_aliases(samples)
            saved = self.alias_store.save(aliases) if aliases else ()
            self._safe_after(self._finish_calibration, saved, tuple(samples), "")
        except VoiceCancelledError:
            return
        except VoiceError as exc:
            self._safe_after(self._finish_calibration, (), tuple(samples), str(exc))
        except OSError as exc:
            self._safe_after(
                self._finish_calibration,
                (),
                tuple(samples),
                f"Não consegui salvar a calibração: {exc}",
            )

    def _show_calibration_prepare(self, index: int) -> None:
        if not self.calibrating:
            return
        self.calibrate_button.configure(text=f"Calibrando {index}/5...")
        self.status_var.set(f"Amostra {index}/5 — prepare-se...")

    def _show_calibration_prompt(self, index: int) -> None:
        if not self.calibrating:
            return
        self.status_var.set(f"Amostra {index}/5 — diga “Huli” agora")

    def _show_calibration_sample(self, index: int, heard: str) -> None:
        if not self.calibrating:
            return
        recognized = " ".join(str(heard or "").split())[:50]
        self.status_var.set(f"Amostra {index}/5 entendida como “{recognized}”")

    def _show_calibration_timeout(self, index: int) -> None:
        if not self.calibrating:
            return
        self.status_var.set(f"Amostra {index}/5 sem fala reconhecida; continuando...")

    def _finish_calibration(
        self,
        aliases: tuple[str, ...],
        samples: tuple[str, ...],
        error: str,
    ) -> None:
        if not self.calibrating:
            return
        self.calibrating = False
        self.calibrate_button.configure(state="normal", text="🎯 Calibrar nome")
        self.wake_button.configure(state="normal")
        if aliases:
            self.wake_aliases = aliases
            if self.wake:
                self.wake.set_aliases(aliases)
            learned = ", ".join(f"“{alias}”" for alias in aliases)
            self._append(
                "Huli",
                f"Calibração concluída. O detector fonético confirmou {learned}.",
            )
        elif error:
            self._append("Huli", f"Não consegui concluir a calibração: {error}")
        else:
            heard = sorted(
                {normalize_text(sample) for sample in samples if normalize_text(sample)}
            )
            detail = ", ".join(f"“{item}”" for item in heard[:5]) or "nenhuma forma"
            self._append(
                "Huli",
                "O detector fonético não confirmou Huli/Ruli pelo menos duas vezes. "
                f"Resultado: {detail}. Tente novamente mais perto do microfone.",
            )
        if self._wake_was_enabled and self.wake and self.wake.enabled:
            self.wake.resume()
            self.listen_button.configure(state="disabled")
            self.status_var.set("Escuta contínua ligada — diga “Huli”")
        else:
            self.listen_button.configure(state="normal")
            self.status_var.set("Escuta contínua desligada")
        self._wake_was_enabled = False

    def _poll_wake(self) -> None:
        if self._closed:
            return
        if self.wake:
            event = self.wake.get_event()
            while event is not None:
                if event.kind is WakeEventKind.COMMAND:
                    self._append("Você [voz]", redact_private_text(event.text))
                    self._execute(event.text, from_wake=True)
                elif event.kind is WakeEventKind.HEARD:
                    self.status_var.set(event.text)
                else:
                    message = event.text.removeprefix("Huli: ")
                    self._append("Sistema", message)
                event = self.wake.get_event()
        self.root.after(60, self._poll_wake)

    def logout(self) -> None:
        self._end_session()
        self._show_login()

    def _end_session(self) -> None:
        if self.calibrating:
            self.calibrating = False
            self._calibration_cancel.set()
        if self.wake:
            self.wake.stop()
            self.wake = None
        session = self.session
        if session:
            self.runtime.context.clear(session.session_id)
            if session.token:
                self.runtime.auth.revoke_token(session.token)
        self.session = None
        self.pending_wake_command = None

    def close(self) -> None:
        self._closed = True
        self._end_session()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    try:
        HuliPanel(root)
    except Exception as exc:
        root.withdraw()
        messagebox.showerror("H.U.L.I.", f"Não foi possível abrir o painel:\n{exc}")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
