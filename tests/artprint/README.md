# Tests ArtPrint – étape 1 (le plateau tourne, il ne bascule plus)

## Lancer le test

Depuis le dossier principal du dépôt :

```
python tests/artprint/run_all.py
```

Il faut Python et les bibliothèques `numpy`, `trimesh`, `shapely`, `manifold3d` et `matplotlib`
(`python -m pip install numpy trimesh shapely manifold3d matplotlib`).

## Ce que fait le test

1. Il crée une pièce test : un bloc de 30 × 30 × 20 mm avec un bras de 25 mm qui dépasse sur le côté.
2. Il la découpe 3 fois avec le slicer modifié :
   - `flat` : une seule direction, à plat (comme une imprimante normale) ;
   - `tilt45` : le bras est découpé avec un plan incliné à 45°, tourné vers +X ;
   - `tilt45_phi90` : pareil, mais tourné vers +Y, pour tester la rotation du plateau.
3. Il compare chaque G-code à celui du Fractal Cortex d'origine (dossier `reference/`) et vérifie :
   - qu'il n'y a plus de moteur de bascule du plateau (`stepper_b`) ni de déplacement `X0 Y-175` ;
   - que la buse ne descend jamais sous le plateau ;
   - que le premier morceau (à plat) est exactement le même qu'avant ;
   - que les morceaux inclinés sont les mêmes trajectoires qu'avant, simplement plus « remises à plat » ;
   - que la quantité de filament est la même ;
   - que, dans un morceau incliné, les points sont bien sur des plans parallèles espacés d'une couche.
4. Il enregistre le G-code et une image 3D de chaque essai dans `tests/artprint/output/`.

Si tout va bien, la dernière ligne affichée est `ALL TESTS PASSED`.
