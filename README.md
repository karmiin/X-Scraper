# 🐍 Twitter (X) Scraper con Proxy e Lista Account

Questo progetto è uno **scraper per X (ex Twitter)** scritto in **Python**, che consente di raccogliere dati da una lista di account, utilizzando una lista di **proxy** per evitare limiti e ban.

## 🔧 Funzionalità

- Lettura di una lista di account da file `.csv`
- Utilizzo automatico di proxy per ogni richiesta
- Rotazione dei proxy per evitare blocchi
- Logging degli account processati e degli errori

## 📁 Struttura dei file

- `accounts.csv`: lista degli username da analizzare (uno per riga, senza `@`)
- `proxies.txt`: lista di proxy in formato `ip:porta` (uno per riga)
- `scraper.py`: script principale per eseguire lo scraping
