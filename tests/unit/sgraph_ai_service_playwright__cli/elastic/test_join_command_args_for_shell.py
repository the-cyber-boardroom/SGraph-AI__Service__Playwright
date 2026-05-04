# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for join_command_args_for_shell helper used by `sp el exec`
# Regression for a shlex.join behaviour: when the user pre-composes a shell
# command into a single quoted string (`sp el exec STACK -- "grep X /etc/hosts"`),
# shlex.join wraps the whole thing again in single quotes, making the remote
# shell treat the literal "grep X /etc/hosts" as the command name. The fix:
# pass single-element argv through unchanged.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from scripts.elastic                                                                import join_command_args_for_shell


class test_join_command_args_for_shell(TestCase):

    def test_single_pre_composed_command_passes_through_unchanged(self):             # The bug: user typed `sp el exec STACK -- "grep ELASTIC_PASSWORD /opt/sg-elastic/.env"` and got "/.../script.sh: 'grep ELASTIC_PASSWORD /opt/sg-elastic/.env': No such file or directory" because shlex.join wrapped the whole pre-quoted string in single quotes.
        cmd = join_command_args_for_shell(['grep ELASTIC_PASSWORD /opt/sg-elastic/.env'])
        assert cmd == 'grep ELASTIC_PASSWORD /opt/sg-elastic/.env'

    def test_multiple_unquoted_args_are_shlex_joined(self):                          # Multi-word case: still need shlex.join so individual args with shell metacharacters get escaped properly
        cmd = join_command_args_for_shell(['docker', 'ps'])
        assert cmd == 'docker ps'

    def test_multiple_args_with_spaces_get_quoted(self):                             # Defensive: if a single arg contains spaces, shlex.join still quotes it for safety
        cmd = join_command_args_for_shell(['bash', '-c', 'echo hello world'])
        assert "'echo hello world'" in cmd or 'echo hello world' in cmd
        assert cmd.startswith('bash -c ')

    def test_empty_list_returns_empty_string(self):
        assert join_command_args_for_shell([]) == ''
