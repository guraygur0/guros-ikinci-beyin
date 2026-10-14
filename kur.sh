#!/usr/bin/env bash
# GurOS — tek satırlık kurulum (macOS / Linux)
#
#   curl -fsSL https://raw.githubusercontent.com/guraygur0/guros-ikinci-beyin/main/kur.sh | bash
#
# Ne yapar: Python 3.9+ bulur, GurOS'u ~/guros-ikinci-beyin klasörüne indirir ya da günceller, sonra soru soran
# kurulumu (kur.py) başlatır. Sen onaylamadan vault'una hiçbir şey yazılmaz.
#
# Ortam değişkenleri (test ve ileri kullanım):
#   GUROS_KAYNAK  indirme yapma, bu klasördeki kur.py'yi çalıştır
#   GUROS_HEDEF   indirilecek klasör (varsayılan: ~/guros-ikinci-beyin)
#
# Her şey bir fonksiyonun içinde ve en sonda çağrılıyor: bağlantı yarıda koparsa yarım betik çalışmaz.

set -euo pipefail

guros_tty_var() {
  { true </dev/tty; } 2>/dev/null
}

guros_sor() {
  local cevap=""
  if guros_tty_var; then
    read -r -p "$1" cevap </dev/tty || cevap=""
  fi
  case "$cevap" in
    h|H|hayır|hayir|n|N|no) return 1 ;;
    *) return 0 ;;
  esac
}

guros_python_bul() {
  local aday
  for aday in python3 python; do
    if command -v "$aday" >/dev/null 2>&1 &&
       "$aday" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
      echo "$aday"
      return 0
    fi
  done
  return 1
}

guros_kur() {
  local depo="https://github.com/guraygur0/guros-ikinci-beyin"
  local py hedef gecici
  if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    printf '\n  \033[35mGurOS kurulumu başlıyor\033[0m\n'
  else
    printf '\n  GurOS kurulumu başlıyor\n'
  fi

  if ! py="$(guros_python_bul)"; then
    echo "  Python 3.9 veya üstü bulunamadı."
    if [ "$(uname)" = "Darwin" ] && command -v brew >/dev/null 2>&1 && guros_sor "  Homebrew ile Python kurulsun mu? [E/h] "; then
      brew install python
      py="$(guros_python_bul)" || py=""
    fi
    if [ -z "${py:-}" ]; then
      if [ "$(uname)" = "Darwin" ]; then
        echo "  Kur: https://www.python.org/downloads/  (ya da Homebrew ile: brew install python)"
      else
        echo "  Kur: sudo apt install python3   ·   Fedora: sudo dnf install python3   ·   Arch: sudo pacman -S python"
      fi
      echo "  Sonra bu komutu yeniden çalıştır."
      return 1
    fi
  fi

  if [ -n "${GUROS_KAYNAK:-}" ]; then
    hedef="$GUROS_KAYNAK"
  else
    hedef="${GUROS_HEDEF:-$HOME/guros-ikinci-beyin}"
    if [ -d "$hedef/.git" ] && command -v git >/dev/null 2>&1; then
      echo "  GurOS güncelleniyor…"
      git -C "$hedef" pull --ff-only -q || echo "  (güncellenemedi; eldeki sürümle devam)"
    elif [ ! -e "$hedef" ] && command -v git >/dev/null 2>&1; then
      echo "  GurOS indiriliyor…"
      git clone -q --depth 1 "$depo.git" "$hedef"
    else
      if [ -e "$hedef" ] && [ ! -f "$hedef/kur.py" ]; then
        echo "  $hedef zaten var ve bir GurOS klasörü değil; taşı ya da sil, sonra yeniden dene."
        return 1
      fi
      echo "  GurOS indiriliyor…"
      gecici="$(mktemp -d)"
      curl -fsSL "$depo/archive/refs/heads/main.tar.gz" | tar -xz -C "$gecici"
      rm -rf "$hedef"
      mv "$gecici/guros-ikinci-beyin-main" "$hedef"
      rm -rf "$gecici"
    fi
  fi

  # "curl | bash" feeds this script through stdin, so the wizard has to read the keyboard from /dev/tty
  if [ "$#" -eq 0 ] && [ ! -t 0 ] && guros_tty_var; then
    "$py" "$hedef/kur.py" </dev/tty
  else
    "$py" "$hedef/kur.py" "$@"
  fi
}

guros_kur "$@"
