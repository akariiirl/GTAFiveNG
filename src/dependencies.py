"""Index flat reader exports without guessing archive/update precedence.

Ambiguous names require an explicit export filename override. YTYP assetName
aliases resolve only supported standalone YDR/YFT exports; YDD members and
texture dictionary inheritance remain unresolved and are reported for local work.
"""
import collections
import xml.etree.ElementTree as ET


def resolve(source, overrides=None):
    candidates = collections.defaultdict(list)
    for pattern in ('*.ydr.xml', '*.yft.xml'):
        for path in sorted(source.glob(pattern)):
            candidates[path.name.split('.rpf_')[-1][:-8].lower()].append(path)
    overrides = overrides or {}
    resolved = {}; ambiguous = {}
    for name, paths in candidates.items():
        chosen = overrides.get(name)
        if chosen is not None:
            matches = [p for p in paths if p.name == chosen]
            if len(matches) != 1: raise ValueError('Invalid dependency override: ' + name)
            resolved[name] = matches[0]
        elif len(paths) == 1:
            resolved[name] = paths[0]
        else:
            ambiguous[name] = [p.name for p in paths]
    aliases = collections.defaultdict(set)
    for path in sorted(source.glob('*.ytyp.xml')):
        for item in ET.parse(path).getroot().findall('.//archetypes/Item'):
            name, asset = item.findtext('name'), item.findtext('assetName')
            if name and asset: aliases[name.lower()].add(asset.lower())
    for name, assets in aliases.items():
        if name in resolved: continue
        if len(assets) == 1 and next(iter(assets)) in resolved:
            resolved[name] = resolved[next(iter(assets))]
        elif len(assets) > 1:
            ambiguous[name] = sorted(assets)
    return resolved, {'ambiguous_drawables': ambiguous,
                      'unresolved_archetype_assets': {n: sorted(a) for n,a in aliases.items() if n not in resolved},
                      'unsupported_dictionary_exports': [p.name for p in sorted(source.glob('*.ydd.xml'))],
                      'precedence': 'No archive priority inferred; ambiguous names require explicit overrides.'}
