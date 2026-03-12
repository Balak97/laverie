"""
Compile .po files to .mo without needing GNU gettext (msgfmt).
Use when: CommandError: Can't find msgfmt.

  pip install polib
  python manage.py compilemo
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compile locale .po files to .mo using Python (no msgfmt required). Install: pip install polib"

    def handle(self, *args, **options):
        try:
            import polib
        except ImportError:
            self.stderr.write(
                self.style.ERROR(
                    "polib is required. Run: pip install polib"
                )
            )
            return

        locale_dir = Path(settings.BASE_DIR) / "locale"
        if not locale_dir.is_dir():
            self.stderr.write(self.style.ERROR(f"Locale directory not found: {locale_dir}"))
            return

        compiled = 0
        for lang_dir in locale_dir.iterdir():
            if not lang_dir.is_dir():
                continue
            lc_messages = lang_dir / "LC_MESSAGES"
            if not lc_messages.is_dir():
                continue
            for po_path in lc_messages.glob("*.po"):
                mo_path = po_path.with_suffix(".mo")
                try:
                    po = polib.pofile(str(po_path))
                    po.save_as_mofile(str(mo_path))
                    self.stdout.write(self.style.SUCCESS(f"Compiled: {po_path.relative_to(locale_dir)} -> {mo_path.name}"))
                    compiled += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error compiling {po_path}: {e}"))

        if compiled:
            self.stdout.write(self.style.SUCCESS(f"Done. {compiled} file(s) compiled."))
        else:
            self.stdout.write("No .po files found in locale/*/LC_MESSAGES/.")
