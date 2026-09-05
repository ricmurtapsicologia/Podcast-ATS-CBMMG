from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
index = (ROOT / "index.html").read_text(encoding="utf-8")
auth_js = (ROOT / "podcast-auth.js").read_text(encoding="utf-8")
auth_css = (ROOT / "podcast-auth.css").read_text(encoding="utf-8")

# Separação de identidade e sessão.
assert 'class="gav-auth-pending"' in index
assert 'data-cats-auth' in index
assert 'podcast-auth.css?v=20260905-2' in index
assert 'podcast-auth.js?v=20260905-1' in index
assert 'https://ricmurtapsicologia.github.io/Curso-ATS/auth.js?v=20260905-2' in index
assert '/Curso-ATS/auth.css' not in index
assert 'gav_auth_v1' in auth_js
assert 'gav_login_attempts_v1' in auth_js
assert 'curso_ats_auth_v3: "gav_auth_v1"' in auth_js
assert 'ats_login_attempts_v3: "gav_login_attempts_v1"' in auth_js

# Branding próprio da ampulheta.
for marker in (
    'Girando a <span class="cats-auth-accent">Ampulheta</span> da Vida',
    'Acesso à biblioteca',
    'Entrar na biblioteca',
    'assets/img/hero.jpg',
):
    assert marker in auth_js or marker in auth_css, marker

# Visual local: nenhum asset visual da tela de bloqueio vem de Pinterest/Pexels.
assert 'pinimg.com' not in auth_css
assert 'images.pexels.com' not in auth_css
assert 'url("assets/img/hero.jpg")' in auth_css

# Fail-closed e privacidade de indexação.
assert 'gav-auth-failed' in auth_js and 'gav-auth-failed' in auth_css
assert '<meta name="robots" content="noindex,nofollow" />' in index

# Acessibilidade e responsividade do gate.
for marker in ('focus-visible', 'prefers-reduced-motion:reduce', '@media(max-width:980px)', '@media(max-width:560px)'):
    assert marker in auth_css, marker

print("PASS: autenticação GAV isolada, branding próprio, ampulheta local, fail-closed, noindex e responsividade.")
