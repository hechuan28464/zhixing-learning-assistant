$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
$voiceRoot=Split-Path -Parent $PSScriptRoot
$videoPlan=Get-Content -LiteralPath (Join-Path $voiceRoot 'src\plan.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$narrator=New-Object System.Speech.Synthesis.SpeechSynthesizer
$narrator.SelectVoice('Microsoft Yaoyao')
$narrator.Rate=2
$narrator.Volume=100
$audioFormat=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(24000,[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,[System.Speech.AudioFormat.AudioChannel]::Mono)
foreach($scene in $videoPlan){
 for($voiceIndex=0;$voiceIndex -lt $scene.sentences.Count;$voiceIndex++){
  $voiceFile=Join-Path $voiceRoot ('public\audio\'+$scene.id+'-'+$voiceIndex+'.wav')
  $narrator.SetOutputToWaveFile($voiceFile,$audioFormat)
  $narrator.Speak($scene.sentences[$voiceIndex])
  $narrator.SetOutputToNull()
 }
 Write-Output ('Narration ready: '+$scene.id)
}
$narrator.Dispose()
