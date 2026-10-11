# Reverse-Search-Bot

Telegram-Bot für die Rückwärts-Bildersuche. Du schickst ihm ein Bild, er schickt dir die Quellen-Links.
Optimiert für **gezeichnete Bilder (Anime, Manga, Furry, Hentai/NSFW)**, findet über die Zusatz-Buttons aber auch normale SFW-Bilder und Fotos.

## Was durchsucht wird

| Dienst | Abdeckung | Ergebnis im Chat |
|---|---|---|
| **SauceNAO** | Pixiv, Danbooru, Gelbooru, Sankaku, e621, FurAffinity, DeviantArt, Twitter/X, nhentai, E-Hentai, Anime, Manga … | ✅ (API-Key nötig, kostenlos) |
| **IQDB** | Danbooru, Gelbooru, yande.re, Konachan, Sankaku, Zerochan, E-Shuushuu, Anime-Pictures | ✅ |
| **Fluffle** | Furry-Art: e621, FurAffinity, Weasyl, Inkbunny, Twitter … (inkl. NSFW) | ✅ |
| Google Lens, Yandex, Bing, TinEye, ascii2d, trace.moe | allgemeine Bilder, Fotos, Anime-Szenen | 🔘 als Buttons |

Die Treffer aller Dienste werden zusammengeführt, doppelte Links entfernt und nach Ähnlichkeit sortiert
(🟢 ≥ 90 %, 🟡 ≥ 75 %, 🟠 darunter, 🔞 = NSFW-Quelle).

Unterstützt werden Fotos, Bilder als Datei (bessere Qualität → bessere Treffer), Sticker, GIFs/Videos (Vorschaubild)
und Bild-Links. In Gruppen antwortest du mit `/sauce` auf ein Bild.

## Einrichtung

1. Bei [@BotFather](https://t.me/BotFather) mit `/newbot` einen Bot anlegen und den Token kopieren.
2. Kostenlosen SauceNAO-Account anlegen und den API-Key holen: <https://saucenao.com/user.php?page=search-api>
   (Free: 100 Suchen/Tag, 4 pro 30 Sekunden).
3. Deine Telegram-User-ID herausfinden (z. B. über [@userinfobot](https://t.me/userinfobot)).
4. Konfiguration anlegen:
   ```bash
   cp .env.example .env
   # TELEGRAM_BOT_TOKEN, SAUCENAO_API_KEY und ALLOWED_USER_IDS eintragen
   ```

### Starten mit Docker

```bash
docker compose up -d --build
```

### Starten ohne Docker (Python ≥ 3.10)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m bot
```

## Konfiguration (`.env`)

| Variable | Standard | Beschreibung |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | – | **Pflicht.** Token von @BotFather |
| `SAUCENAO_API_KEY` | – | Stark empfohlen, sonst wird SauceNAO übersprungen |
| `ALLOWED_USER_IDS` | leer (= alle) | Kommagetrennte User-IDs, die den Bot benutzen dürfen |
| `MIN_SIMILARITY` | `60` | Treffer darunter werden ausgeblendet |
| `MAX_RESULTS` | `8` | Maximale Anzahl Treffer pro Antwort |
| `ENABLE_SAUCENAO` / `ENABLE_IQDB` / `ENABLE_FLUFFLE` | `true` | Dienste einzeln abschalten |
| `PUBLIC_UPLOAD` | `litterbox` | Bild für 1 h bei litterbox.catbox.moe hochladen, um die Buttons (Google Lens, Yandex …) zu erzeugen. `none` = aus |
| `CONTACT` | – | Dein Name/Kontakt für den User-Agent (Fluffle verlangt das) |

### Datenschutz-Hinweis

Das Bild wird an SauceNAO, IQDB und Fluffle geschickt. Mit `PUBLIC_UPLOAD=litterbox` wird es außerdem für eine Stunde
öffentlich (unter einer zufälligen URL) bei litterbox.catbox.moe abgelegt, weil Google, Yandex & Co. nur per URL suchen können.
Die Telegram-Datei-URL wird dafür bewusst **nicht** verwendet, da sie den Bot-Token enthält.
Wer das nicht möchte, setzt `PUBLIC_UPLOAD=none`.

## Entwicklung

```bash
pip install -r requirements-dev.txt
pytest
```
