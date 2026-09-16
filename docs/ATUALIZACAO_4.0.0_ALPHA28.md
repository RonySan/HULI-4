# Perfil vocal do proprietário — alpha.28

## Uso

1. Encerre a Huli pelo botão Encerrar Huli (fechar a janela apenas minimiza).
2. Abra INICIAR_PAINEL.bat e clique em Minha voz.
3. Leia as cinco frases em tom natural, apenas quando aparecer Fale agora.
4. Ligue a escuta contínua, diga Huli, espere Estou ouvindo e fale uma frase
   completa, por exemplo: Huli, por favor me diga que horas são agora.
5. Teste também pelo botão Ouvir agora e com outra pessoa falando o mesmo comando.
   Uma rejeição não executa o texto. Use Apagar perfil vocal para excluir o cadastro.

O teclado continua disponível. O cadastro é local e substitui um perfil anterior
somente depois de verificar a consistência das cinco amostras. Arquivos de áudio
não são guardados; características biométricas são protegidas com DPAPI em
data/secrets/owner_voice_profile.json, fora do Git.

## Funcionamento e limites

O detector do nome ainda pode reagir a qualquer pessoa. A identificação ocorre
na frase do comando, antes de enviá-la ao Whisper e ao executor. Dizer apenas Huli
é curto demais para identificar um locutor. Falas curtas, ruído, voz alterada ou
amostras inconsistentes são recusados. O filtro não permite alternar silenciosamente
para Vosk/Windows sem verificação caso o Whisper esteja indisponível.

O modelo treinado de locutor substitui o protótipo de comparação espectral simples.
O limiar inicial de similaridade é 0,75 e exige concordância de pelo menos três
referências. Não há taxa de acerto validada para Rony: testes automatizados verificam
bloqueios e integração, não a precisão biométrica real. É necessário testar o cadastro
com Rony e outra pessoa. Não há detecção de gravações ou voz clonada. Isto não
substitui a senha do Windows nem desbloqueia o diário criptografado.

HULI_VOICE_OWNER_ONLY=true é o padrão. Desativar essa configuração permite comandos
de qualquer voz; os iniciadores com voz explicitamente mantêm true.

## Modelo e reprodução

Modelo Apache-2.0: [Vosk speaker identification 0.4](https://alphacephei.com/vosk/models).
O [exemplo oficial](https://github.com/alphacep/vosk-api/blob/master/python/example/test_speaker.py)
recomenda frases de mais de quatro segundos para melhores vetores de locutor.
Use também o modelo português em models/vosk-pt, já instalado nesta Huli.

Download único: https://alphacephei.com/vosk/models/vosk-model-spk-0.4.zip
Extraia a pasta vosk-model-spk-0.4 dentro de models. Nenhum download ocorre durante
as conversas. SHA256 do ZIP instalado:
A74D8F51144484813E16AF689BB0F916B7A111E2347F467C4933C1166097B5A7.

O modelo carregou nesta instalação e recusou silêncio real sintetizado como PCM.
Não foi aberto o microfone nem criado um perfil do usuário durante os testes.

Validação: suíte completa com 404 testes aprovados e um teste adicional de
inicialização do painel aprovado, em banco temporário e janela oculta.
