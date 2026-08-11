from __future__ import annotations

"""Executa a fase full do N3 na ordem literal do plano mestre.

Ordem obrigatória:
1. Série 1 -> QA Série 1
2. Série 2 -> QA Série 2
3. Série 3 -> QA Série 3
4. QA comparativo final

O paralelismo existe somente dentro de cada série. Não altera texto, voz,
prosódia, pausas ou pós-produção definidos pelo motor N3 aprovado no A/B.
"""

import asyncio
import json

import n3_runner as r

p = r.p


async def ordered_run_full(manifest: dict, directions: dict[tuple[str, str], dict], cfg: dict) -> None:
    engine = cfg.get('selected_engine', 'N3-edge-semantic')
    if engine != 'N3-edge-semantic':
        raise RuntimeError(
            'A promoção automática só é permitida para N3-edge-semantic até existir aprovação auditiva explícita de outro motor.'
        )

    voice_sem = asyncio.Semaphore(r.FULL_VOICE_CONCURRENCY)
    episode_sem = asyncio.Semaphore(r.FULL_EPISODE_CONCURRENCY)

    async def process(item: dict) -> dict:
        series, episode = item['series'], item['episode']
        direction = directions[(series, episode)]
        out = p.final_audio_path(series, episode)
        async with episode_sem:
            await r.synth_full_episode(direction, out, voice_sem)
            rec = p.qa_record(series, episode, engine, out, direction)
        if rec['status'] != 'pass':
            raise RuntimeError(f'QA falhou em {series}/{episode}: {rec["issues"]}')
        return rec

    all_qa: list[dict] = []
    execution_order = ['serie-1', 'serie-2', 'serie-3']

    for series in execution_order:
        items = [item for item in manifest['episodes'] if item['series'] == series]
        series_qa = await asyncio.gather(*(process(item) for item in items))
        if not series_qa or not all(rec['status'] == 'pass' for rec in series_qa):
            raise RuntimeError(f'Gate de QA da {series} não foi integralmente aprovado.')

        all_qa.extend(series_qa)
        p.REPORTS.mkdir(parents=True, exist_ok=True)
        (p.REPORTS / f'qa-{series}.json').write_text(
            json.dumps({
                'phase': 'series-qa',
                'series': series,
                'engine': engine,
                'episodes': len(series_qa),
                'all_pass': True,
                'qa': series_qa,
            }, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )

    # Só depois do QA integral das três séries as referências públicas podem mudar.
    p.patch_audio_references()

    summary = {
        'phase': 'full',
        'engine': engine,
        'execution_order': execution_order,
        'parallelism_policy': 'paralelismo somente dentro de cada série; séries executadas sequencialmente',
        'parallel_voice_concurrency': r.FULL_VOICE_CONCURRENCY,
        'parallel_episode_concurrency': r.FULL_EPISODE_CONCURRENCY,
        'episodes': len(all_qa),
        'series_counts': {
            s: len([rec for rec in all_qa if rec['series'] == s])
            for s in execution_order
        },
        'all_pass': all(rec['status'] == 'pass' for rec in all_qa),
        'qa': all_qa,
    }
    (p.REPORTS / 'full-qa-report.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )


p.run_full = ordered_run_full


if __name__ == '__main__':
    asyncio.run(p.main())
