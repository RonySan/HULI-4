"""Diagnóstico real de voz. Sem banco pessoal; microfone só mediante opção."""

from __future__ import annotations

import argparse
from array import array

from huli.infrastructure.config import load_settings
from huli.security.privacy import redact_private_text
from huli.voice import VoiceError, VoiceService


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--speak", action="store_true", help="Reproduzir uma frase de teste.")
    parser.add_argument("--listen", action="store_true", help="Ouvir uma frase por até 20 segundos, sem executá-la.")
    parser.add_argument("--microphone-test", action="store_true", help="Abrir microfone por 2 segundos e mostrar somente nível de sinal.")
    args = parser.parse_args()
    settings = load_settings()
    service = VoiceService.local_default(language=settings.voice_language, input_timeout=20,
        rate=settings.voice_rate, volume=settings.voice_volume,
        input_provider=settings.voice_input_provider, model_path=settings.voice_model_path,
        input_device=settings.voice_input_device)
    try:
        capabilities = service.capabilities()
        print(capabilities.detail, flush=True)
        if not capabilities.output_available or not capabilities.input_available:
            print("CONFIGURAÇÃO INCOMPLETA: fala e escuta precisam estar disponíveis.")
            return 1
        if capabilities.provider == "windows-tts+vosk-offline":
            service.backend.vosk.prepare()
            print("Modelo português carregado localmente.", flush=True)
        if args.speak:
            service.speak("Olá, Rony. Minha voz está pronta. Vamos testar a escuta em português.")
            print("Síntese executada. Confirme se você ouviu a frase.", flush=True)
        if args.microphone_test:
            import sounddevice as sd
            info = sd.query_devices(settings.voice_input_device, "input")
            rate = int(info["default_samplerate"])
            print("Microfone ligado por 2 segundos; áudio não será salvo ou transcrito.", flush=True)
            peak = 0
            overflowed = False
            with sd.RawInputStream(device=settings.voice_input_device, samplerate=rate, channels=1, dtype="int16") as stream:
                for _ in range(10):
                    data, overflow = stream.read(rate // 5)
                    values = array("h", bytes(data))
                    peak = max(peak, max((abs(value) for value in values), default=0))
                    overflowed |= overflow
            print(f"Microfone encerrado. Pico do sinal: {peak}/32768; perda de áudio: {overflowed}.")
            if overflowed or peak == 0:
                print("A abertura funcionou, mas o sinal precisa ser verificado com você falando.")
                return 1
        if args.listen:
            print("Diga 'que horas são' ou 'o que temos na agenda'. Escuta por até 20 segundos; Ctrl+C cancela.", flush=True)
            print(f"Ouvi: {redact_private_text(service.listen_once())}")
            print("Nenhuma ação foi executada; este é apenas um teste de transcrição.")
        if not args.listen:
            print("Configuração verificada. A compreensão da sua fala ainda exige o teste --listen.")
        return 0
    except KeyboardInterrupt:
        print("\nTeste cancelado; microfone encerrado.")
        return 1
    except (VoiceError, OSError, ValueError) as exc:
        print(f"Teste não aprovado: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
