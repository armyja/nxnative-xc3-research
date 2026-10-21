"""Build-time stage preflight for dmsh_build.py.

Geometry programs have no encoding path downstream: dm/gfx/nvn/nvn_mtl.m binds only pr->sh[0] (vertex) and
pr->sh[1] (fragment) into a pipeline and Metal has no geometry stage at all, so a translated geometry shader
would be written into the library, load, and never run. Rather than let a build report success while a selected
stage silently cannot execute, a selection that includes one stops the build.

The check runs on the keys the build actually selected, before any cache lookup, dispatch or output, so a
cached entry cannot bypass it. It says nothing about a map that merely contains geometry: only the selection
matters, and an explicit vertex / pixel / compute subset builds as before.
"""

GEOMETRY = 'gs'

_NO_PATH = ('the Metal backend encodes only the vertex and fragment stages (dm/gfx/nvn/nvn_mtl.m binds '
            'pr->sh[0] and pr->sh[1]), so this shader would load and never run')


def stage_of_key(key, loc, stage_of):
    """The stage dmsh_build will use for `key`, by the same rule job_for uses.

    An embedded row (dmsh_build's `main.rodata@` entries) carries its stage in the mapping table; a package
    record carries it in the first two characters of its file name.
    """
    return stage_of.get(key, loc[key][0][:2])


def unsupported(keys, loc, stage_of):
    """[(key, source, stage)] for the selected keys whose stage has no encoding path."""
    bad = []
    for key in keys:
        stage = stage_of_key(key, loc, stage_of)
        if stage == GEOMETRY:
            name, off = loc[key]
            bad.append((key, f'{name}#{off}', stage))
    return bad


def refusal_lines(bad):
    """The [RED] lines a refused selection prints; each names the key and where it came from."""
    return [f'[RED] {key} ({src}): unsupported geometry stage {stage} - {_NO_PATH}' for key, src, stage in bad]
