#!/usr/bin/env python
"""Script d'entrée Django pour Dortoir 3."""
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django n'est pas installé. Lancez: pip install django"
        ) from exc
    execute_from_command_line(sys.argv)
