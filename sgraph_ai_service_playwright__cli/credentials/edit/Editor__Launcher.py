# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Credentials — Editor__Launcher
#
# Launches the user's preferred editor on the given path.  Respects $VISUAL,
# then $EDITOR, then falls back to 'vi'.  Tests substitute
# Editor__Launcher__In_Memory to avoid opening a real editor.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Editor__Launcher(Type_Safe):

    def launch(self, path: str) -> None:
        import subprocess
        import os
        editor = os.environ.get('VISUAL') or os.environ.get('EDITOR') or 'vi'
        subprocess.run([editor, path], check=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Editor__Launcher__In_Memory — test seam
# ═══════════════════════════════════════════════════════════════════════════════

class Editor__Launcher__In_Memory(Editor__Launcher):

    captured_path : str = ''
    write_content : str = ''    # if set, write this to the file instead of opening editor

    def launch(self, path: str) -> None:
        self.captured_path = path
        if self.write_content:
            with open(path, 'w') as f:
                f.write(self.write_content)
