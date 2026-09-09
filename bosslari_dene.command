#!/bin/zsh
cd -- "${0:A:h}" || exit 1
print 'TURN THE PAGE — Boss denemesi (ana kayit degismez)'
print '1 Pergel   2 Aranan afis   3 Zimba treni'
print '4 Yorunge  5 Makas        6 Final Editor'
read -r 'boss_choice?Boss numarasi [1-6]: '
case "$boss_choice" in
  1) exec python3 practice.py --page 1 --room moon_gate_duel --boss ;;
  2) exec python3 practice.py --page 2 --room marker_margin_trial --boss ;;
  3) exec python3 practice.py --page 2 --room midnight_train --boss ;;
  4) exec python3 practice.py --page 3 --room zero_garden --boss ;;
  5) exec python3 practice.py --page 4 --room scissor_office --boss ;;
  6) exec python3 practice.py --page 5 --room final_margin_revision --boss ;;
  *) print '1 ile 6 arasinda bir boss sec.' ;;
esac
