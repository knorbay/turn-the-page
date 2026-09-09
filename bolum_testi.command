#!/bin/zsh
cd -- "${0:A:h}" || exit 1
print 'TURN THE PAGE — Bolum denemesi (ana kayit degismez)'
print '1 Ronin   2 Vahsi Bati   3 Uzay   4 Ajan   5 Son Taslak'
read -r 'beta_page?Bolum numarasi [1-5]: '
case "$beta_page" in
  [1-5]) exec python3 practice.py --page "$beta_page" ;;
  *) print '1 ile 5 arasinda bir bolum sec.' ;;
esac
