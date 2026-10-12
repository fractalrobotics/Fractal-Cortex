# Tests ArtPrint – étape 1 (le plateau tourne, il ne bascule plus)

Rappel des axes d'ArtPrint : X = le plateau avance/recule, Y = la buse va de droite à gauche (15 cm, du centre du plateau au bord),
Z = la buse monte/descend, A = le plateau tourne sur son centre, B = la tête s'incline (pas encore géré).

## Lancer le test

Depuis le dossier principal du dépôt :

```
python tests/artprint/run_all.py
```

Il faut Python et les bibliothèques `numpy`, `trimesh`, `shapely`, `manifold3d` et `matplotlib`
(`python -m pip install numpy trimesh shapely manifold3d matplotlib`).

## Ce que fait le test

1. Il crée une pièce test : un bloc de 30 × 30 × 20 mm avec un bras de 25 mm qui dépasse sur le côté.
2. Il découpe 5 pièces avec le slicer modifié :
   - `flat` : le bloc, une seule direction, à plat ;
   - `tilt45` : le bras du bloc est découpé avec un plan incliné à 45°, tourné vers +X ;
   - `tilt45_phi90` : pareil, mais tourné vers +Y ;
   - `ring` : un anneau de 20 cm autour du centre du plateau, que la buse ne peut faire qu'en tournant le plateau pendant chaque tour ;
   - `far_half` : un bloc sur la moitié du plateau que la buse n'atteint pas sans tourner le plateau.
3. Il compare chaque G-code à celui du Fractal Cortex d'origine (dossier `reference/`) et vérifie :
   - qu'il n'y a plus de moteur de bascule du plateau (`stepper_b`) ni de déplacement `X0 Y-175` ;
   - que la buse ne descend jamais sous le plateau ;
   - que tous les mouvements restent dans la course de la machine (Y entre 0 et 15 cm, X entre −15 et +15 cm) ;
   - que, une fois la rotation du plateau « défaite », les lignes imprimées sont exactement celles de l'original ;
   - que les morceaux inclinés redonnent l'original quand on remet l'ancienne bascule, et que le plateau ne tourne pas pendant ces morceaux ;
   - que la vitesse réelle sur la pièce est bien celle des réglages, même quand le plateau tourne ;
   - que le plateau ne tourne jamais de plus de 0,5° sur une ligne de G-code.
4. Il enregistre le G-code et une image 3D de chaque essai (la pièce telle qu'elle sera sur le plateau) dans `tests/artprint/output/`.

Si tout va bien, la dernière ligne affichée est `ALL TESTS PASSED`.
