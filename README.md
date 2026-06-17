# Top de Noticias Perú — Flash Briefing para Alexa

Genera cada mañana un boletín curado de noticias peruanas (agregando varios medios +
resumen con IA) y lo publica como un feed que tu Echo lee cuando dices:

> *"Alexa, ¿qué noticias hay?"* / *"Alexa, pon mi resumen de noticias"*

---

## 1. Instalación local

```bash
cd ~/projects/alexa-noticias-pe
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # pega tu ANTHROPIC_API_KEY dentro
```

Prueba que genera el feed:

```bash
python generar_feed.py            # con resumen IA
python generar_feed.py --sin-ia   # sin IA (más rápido, para probar)
```

Debe crear `docs/feed.json`. Ábrelo y revisa que se vea bien.

---

## 2. Publicar el feed en GitHub Pages (HTTPS obligatorio)

Amazon exige que el feed esté en una URL pública con HTTPS válido. GitHub Pages lo da gratis.

```bash
cd ~/projects/alexa-noticias-pe
git init && git add . && git commit -m "init"
gh repo create alexa-noticias-pe --private --source=. --push   # o crea el repo a mano
```

Luego en GitHub: **Settings → Pages → Source: Deploy from a branch → Branch: `main` /docs**.

Tu feed quedará en:
```
https://<tu-usuario>.github.io/alexa-noticias-pe/feed.json
```
Ábrela en el navegador para confirmar que carga.

---

## 3. Crear la Flash Briefing Skill (10 min, en tu cuenta Amazon)

1. Entra a https://developer.amazon.com/alexa/console/ask con la **misma cuenta de tu Echo**.
2. **Create Skill** → nombre "Top Noticias Perú" → modelo **Flash Briefing** → Create.
3. En **Flash Briefing → Add new feed**:
   - Preamble: "Tus noticias top de Perú"
   - Name: "Top Noticias Perú"
   - Content type: **Text**
   - Content genre: Headline News
   - Feed (URL): pega tu URL de GitHub Pages (paso 2)
4. Guarda. No necesitas publicarla ni certificarla: queda en **Development** y ya está
   disponible en tu cuenta.

---

## 4. Activarla en tu Echo

1. App **Alexa** → **Más → Configuración → Resumen de noticias** (Flash Briefing).
2. Activa "Top Noticias Perú" y **arrástrala arriba** para que se lea primero.
3. Di: *"Alexa, ¿qué noticias hay?"* 🎉

---

## 5. Automatizar (cron — se actualiza solo cada mañana)

```bash
chmod +x publicar.sh
crontab -e
```
Agrega (corre a las 6:00 AM todos los días):
```
0 6 * * *  /Users/franco.rub/projects/alexa-noticias-pe/publicar.sh >> /Users/franco.rub/projects/alexa-noticias-pe/cron.log 2>&1
```

> Nota: el Mac debe estar encendido a esa hora. Si quieres que corra aunque el Mac esté
> dormido, se puede mover a GitHub Actions (programado en la nube) — pídemelo y lo armo.

---

## Personalizar

- **Qué medios y cuántas noticias:** edita `FUENTES` y `TOP_N` en `generar_feed.py`.
- **Sin IA:** corre con `--sin-ia` o quita la key del `.env`.
- **Verifica las URLs de RSS:** las marcadas en `FUENTES` pueden cambiar; si una falla,
  el script la salta con un aviso y sigue con las demás.

## Fuentes / referencias
- Amazon — [Flash Briefing Skill API](https://developer.amazon.com/en-US/docs/alexa/flashbriefing/understand-the-flash-briefing-skill-api.html)
- Amazon — [Formato del feed](https://developer.amazon.com/en-US/docs/alexa/flashbriefing/flash-briefing-skill-api-feed-reference.html)
- Amazon — [Crear una Flash Briefing Skill](https://developer.amazon.com/en-US/docs/alexa/flashbriefing/create-flash-briefing.html)
