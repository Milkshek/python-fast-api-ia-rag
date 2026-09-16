# Fixtures PDF

`encrypted-aes256.pdf` : document synthétique d'une page vide, créé pour tester le
refus AES-256 sans dépendance cryptographique dans l'application. Aucun contenu
externe ni donnée personnelle. Mot de passe de test : `j5-test-only`.

Génération avec pypdf 6.19.0 et cryptography dans un environnement temporaire :

```python
from pypdf import PdfWriter

writer = PdfWriter()
writer.add_blank_page(width=300, height=300)
writer.encrypt("j5-test-only", algorithm="AES-256")
with open("encrypted-aes256.pdf", "wb") as output:
    writer.write(output)
```

Les autres PDF sont générés en mémoire par les tests, sans dépendance crypto.
