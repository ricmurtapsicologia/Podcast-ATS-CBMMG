# Governança da release N3

## Estado verificado

A branch `main` está atualmente sem branch protection aplicada pelo GitHub.

A conexão GitHub disponível nesta execução permite leitura da proteção, commits, arquivos, workflows, issues e PRs, mas não expõe uma operação de escrita para branch protection/rulesets. Portanto, esta etapa não deve ser marcada como aplicada automaticamente.

## Configuração canônica recomendada para `main`

Aplicar no GitHub, em Settings > Rules > Rulesets (ou Branch protection rules), um ruleset para `main` com:

1. Require a pull request before merging.
2. Require at least 1 approval.
3. Dismiss stale approvals when new commits are pushed.
4. Require status checks to pass before merging.
5. Require branches to be up to date before merging.
6. Status checks obrigatórios:
   - `gate` — workflow `N3 release gate`;
   - `player-smoke` — workflow `Podcast player E2E`.
7. Require conversation resolution before merging.
8. Block force pushes.
9. Block branch deletion.
10. Apply rules to administrators/bypass actors sempre que operacionalmente viável.
11. Não conceder `contents: write` a workflows de teste; manter escrita apenas nos workflows de geração/publicação que realmente precisam publicar artefatos.

## Critério de governança

Até a proteção efetiva ser ativada no GitHub, o estado é:

`PENDENTE — CONFIGURAÇÃO DE BRANCH PROTECTION/RULESET`

Isso não invalida os testes técnicos da release já publicada, mas impede classificar a governança do repositório como integralmente endurecida.

## Rollback

O histórico Git deve permanecer como mecanismo primário de rollback. Não reescrever histórico, não apagar masters anteriores necessárias à recuperação e não usar force-push na `main`.
