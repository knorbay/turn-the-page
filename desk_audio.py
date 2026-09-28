"""An original, phase-aligned desk score: taps, scribbles, muted bell fragments."""
from audio_composer import _pcm

def desk_score(composer,page,energy=0,boss=False):
    beat=60/(76+page*4)
    target=composer.silence(32*beat)
    root=(62,57,65,60,62)[page]
    for i in range(32):
        at=i*beat
        # A student absent-mindedly tapping the pencil. The quiet track breathes.
        if i%4==0 or energy:
            composer._add_impact(target,at,125+page*13,.028+energy*.075,.06,902+i+page*91)
        if energy and i%2:
            composer._add_noise(target,at+beat*.5,.13,.045,600+i,'scratch')
        if i in (0,7,16,23):
            interval=(0,3,7,2)[(i//7)%4]
            composer._add_note(target,at,.8,composer.midi(root+interval),.055,'pencil')
        if boss and i%2==0:
            composer._add_impact(target,at+beat*.5,74,.09,.16,100+i)
            composer._add_noise(target,at+beat*.73,.1,.038,300+i,'paper')
        elif energy and i%8==6:
            composer._add_noise(target,at,.32,.03,500+i,'rub')
    return _pcm(target)
