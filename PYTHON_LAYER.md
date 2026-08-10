# Camada Python — Podcast ATS

## Estado de segurança

A camada de mídia é aditiva e não altera `index.html`, `app.js`, `psp.js`, players, séries ou links atuais.

Ponto de rollback: `backup/pre-python-20260809`.

## Auditoria somente leitura

```bash
python scripts/audio_pipeline.py audit --root .
```

O inventário registra caminho, tamanho, SHA-256 e, quando `ffprobe` está disponível, duração, codec, sample rate, canais e bitrate. Arquivos vazios ou ilegíveis geram falha; duplicidades por hash são reportadas.

A auditoria completa é manual no GitHub Actions para evitar processar desnecessariamente todo o grande acervo a cada commit.

## Normalização sem sobrescrita

```bash
python scripts/audio_pipeline.py normalize --source arquivo.mp3 --output-dir audio-web
```

A normalização usa loudness alvo de -16 LUFS, true peak -1,5 dB, 48 kHz e MP3 160 kbps. O arquivo original é preservado e a saída vai para diretório separado. Por padrão, um derivado existente não é sobrescrito.

## Regra de promoção

Nenhum áudio normalizado substitui automaticamente o acervo publicado. Primeiro comparar e aprovar o derivado; depois atualizar o catálogo/link deliberadamente.
