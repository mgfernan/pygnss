import tempfile

import pygnss.file as file


def test_grep_line():

    with tempfile.NamedTemporaryFile('w+') as fh:

        fh.write("""
        line
        line
        line
        target
        line
        target""")

        fh.read()
        generator = file.grep_lines(fh.name, "target")

        elements = list(generator)

        assert len(elements) == 2
