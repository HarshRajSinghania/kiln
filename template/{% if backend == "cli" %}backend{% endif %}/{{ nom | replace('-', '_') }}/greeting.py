"""Exemple de cœur pur : reçoit des valeurs, renvoie une valeur, ne touche pas au terminal."""


def build_greeting(name: str) -> str:
    return f"Bonjour, {name.strip() or 'monde'} !"
