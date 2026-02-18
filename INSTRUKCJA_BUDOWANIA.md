# Jak zbudować aplikację Android (APK)

Aplikacja została przygotowana przy użyciu frameworka **Kivy** i narzędzia **Buildozer**.
Aby wygenerować plik `.apk`, potrzebujesz systemu Linux (np. Ubuntu) lub WSL (Windows Subsystem for Linux) na Windowsie.

## Krok 1: Instalacja zależności

Otwórz terminal (w systemie Linux lub WSL) i wykonaj poniższe komendy, aby zainstalować wymagane biblioteki:

```bash
# Aktualizacja pakietów
sudo apt update
sudo apt upgrade -y

# Instalacja gita, pythona i narzędzi systemowych
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# Instalacja cython i virtualenv (ważne wersje dla Buildozera)
pip3 install --user --upgrade Cython==0.29.33 virtualenv

# Instalacja buildozera
pip3 install --user buildozer
```

Upewnij się, że katalog `~/.local/bin` jest w twojej ścieżce PATH (zwykle jest domyślnie).

## Krok 2: Przygotowanie projektu

Jeśli jeszcze tego nie zrobiłeś, pobierz ten projekt na dysk:

```bash
git clone <adres-tego-repozytorium>
cd <katalog-repozytorium>
```

Upewnij się, że w katalogu znajduje się plik `buildozer.spec`.

## Krok 3: Budowanie pliku APK

Będąc w katalogu głównym projektu, uruchom komendę:

```bash
buildozer android debug
```

**Uwaga:** Pierwsze uruchomienie może potrwać **bardzo długo** (nawet 15-30 minut), ponieważ Buildozer musi pobrać Android SDK, NDK oraz skompilować wszystkie zależności (Python, Kivy, biblioteki krypto). Bądź cierpliwy.

## Krok 4: Instalacja

Po zakończeniu procesu (jeśli zobaczysz komunikat o sukcesie), plik `.apk` znajdzie się w katalogu `bin/`:

```
bin/tidaltransfer-0.1-arm64-v8a-debug.apk
```

Możesz przesłać ten plik na telefon (np. przez USB, Google Drive, email) i zainstalować go.

## Uwagi

- Aplikacja wymaga przeglądarki do logowania (OAuth). Po kliknięciu "Login" w aplikacji, otworzy się strona Tidala w domyślnej przeglądarce telefonu. Po zalogowaniu wróć do aplikacji.
- Jeśli napotkasz błędy podczas budowania, upewnij się, że masz dużo wolnego miejsca na dysku (ok. 5-10 GB na pliki tymczasowe Android SDK).
